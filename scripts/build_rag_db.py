"""Build a local RAG corpus + Chroma DB for the agriculture chatbot.

Pipeline:
  1) Collect URLs (seeds/RSS/sitemaps)
  2) Scrape content (HTML + optional PDF)
  3) Process at scale with PySpark (clean, dedupe, normalize)
  4) Ingest processed text into Chroma (embeddings via OpenRouter)

Usage (small run):
  python scripts/build_rag_db.py --config scripts/sources.json --max-urls 20 --concurrency 6

Notes:
  - Spark step requires Java + pyspark. If unavailable, use --no-spark.
  - Output artifacts go to ./data by default.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from urllib.parse import urljoin, urldefrag, urlparse

import httpx

from bs4 import BeautifulSoup

from app.services.scraping_service import ScrapingService
from app.services.ingest_service import IngestService


AG_KEYWORDS = {
    "agri",
    "agriculture",
    "farming",
    "farm",
    "crop",
    "crops",
    "soil",
    "irrigation",
    "fertilizer",
    "fertiliser",
    "pesticide",
    "disease",
    "plant",
    "seed",
    "harvest",
    "livestock",
    "dairy",
}


def _is_http_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def _looks_agriculture_related(url: str) -> bool:
    lower = url.lower()
    return any(k in lower for k in AG_KEYWORDS)


def _parse_sitemap(xml_text: str) -> list[str]:
    # Very small sitemap parser (no external deps).
    # Finds all <loc>...</loc> entries.
    return re.findall(r"<loc>(.*?)</loc>", xml_text, flags=re.IGNORECASE)


def _parse_rss(xml_text: str) -> list[str]:
    # Minimal RSS/Atom parser for links.
    # RSS: <item><link>url</link>
    rss_links = re.findall(r"<item[\s\S]*?<link>(.*?)</link>", xml_text, flags=re.IGNORECASE)
    # Atom: <entry>...<link href="..."/>
    atom_links = re.findall(r"<entry[\s\S]*?<link[^>]+href=['\"]([^'\"]+)['\"][^>]*/?>", xml_text, flags=re.IGNORECASE)
    return rss_links + atom_links


async def collect_urls(config_path: Path, max_urls: int) -> list[str]:
    config = json.loads(config_path.read_text(encoding="utf-8"))

    urls: list[str] = []
    seen: set[str] = set()

    def add(u: str):
        u = (u or "").strip()
        if not u or not _is_http_url(u):
            return
        if u in seen:
            return
        seen.add(u)
        urls.append(u)

    for u in config.get("seed_urls", []) or []:
        add(u)

    # Crawl a small set of links from seed pages to discover actual content URLs.
    # This keeps it simple (no JS rendering) but is enough for blogs/docs/manual pages.
    seed_netlocs = {urlparse(u).netloc for u in urls if _is_http_url(u)}

    async def crawl_from_seed(seed_url: str, depth_limit: int = 2, per_seed_limit: int = 200):
        queue: list[tuple[str, int]] = [(seed_url, 0)]
        local_seen: set[str] = set()

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "AgriRAGBot/1.0 (+https://localhost; educational-project)"},
        ) as client:
            while queue and len(urls) < max_urls and len(local_seen) < per_seed_limit:
                current, depth = queue.pop(0)
                if current in local_seen:
                    continue
                local_seen.add(current)

                try:
                    r = await client.get(current)
                    r.raise_for_status()
                except Exception:
                    continue

                content_type = (r.headers.get("content-type") or "").lower()
                if "text/html" not in content_type:
                    continue

                if depth >= depth_limit:
                    continue

                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = str(a.get("href") or "")
                    absolute = urljoin(current, href)
                    absolute, _frag = urldefrag(absolute)
                    if not _is_http_url(absolute):
                        continue
                    parsed = urlparse(absolute)
                    if not parsed.netloc:
                        continue
                    # Keep to known seed domains (strict) to avoid crawling the whole web.
                    if parsed.netloc not in seed_netlocs:
                        continue
                    # Prefer agriculture-looking paths, but still allow some.
                    if _looks_agriculture_related(absolute) or any(x in parsed.path.lower() for x in ("agri", "farm", "crop", "soil", "irrig", "disease")):
                        add(absolute)
                    if len(urls) >= max_urls:
                        break

                # Expand crawl frontier with a smaller set of candidate links
                for a in soup.find_all("a", href=True):
                    href = str(a.get("href") or "")
                    absolute = urljoin(current, href)
                    absolute, _frag = urldefrag(absolute)
                    if not _is_http_url(absolute):
                        continue
                    parsed = urlparse(absolute)
                    if parsed.netloc in seed_netlocs:
                        queue.append((absolute, depth + 1))

    for seed in list(config.get("seed_urls", []) or [])[:10]:
        if len(urls) >= max_urls:
            break
        if _is_http_url(seed):
            await crawl_from_seed(seed)

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for feed in config.get("rss_feeds", []) or []:
            try:
                r = await client.get(feed)
                r.raise_for_status()
                for u in _parse_rss(r.text):
                    add(u)
            except Exception:
                continue

        for sm in config.get("sitemaps", []) or []:
            try:
                r = await client.get(sm)
                r.raise_for_status()
                for u in _parse_sitemap(r.text):
                    add(u)
            except Exception:
                continue

    # Strict-ish filter: keep everything from seeds, but prefer agriculture-looking URLs.
    prioritized = [u for u in urls if _looks_agriculture_related(u)]
    rest = [u for u in urls if u not in set(prioritized)]
    final = prioritized + rest

    return final[:max_urls]


async def scrape_urls(urls: list[str], out_jsonl: Path, concurrency: int) -> int:
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    service = ScrapingService()
    sem = asyncio.Semaphore(concurrency)

    async def scrape_one(url: str) -> dict[str, Any] | None:
        async with sem:
            try:
                data = await service.scrape_url(url)
                content = (data.get("content") or "").strip()
                if len(content) < 200:
                    return None
                return {
                    "url": url,
                    "title": data.get("title") or "",
                    "content": content,
                    "document_type": "pdf" if url.lower().endswith(".pdf") else "webpage",
                }
            except Exception:
                return None

    try:
        results = await asyncio.gather(*(scrape_one(u) for u in urls))
    finally:
        await service.close()

    written = 0
    with out_jsonl.open("w", encoding="utf-8") as f:
        for item in results:
            if not item:
                continue
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            written += 1

    return written


def _python_process_record(rec: dict[str, Any]) -> dict[str, Any] | None:
    content = (rec.get("content") or "").strip()
    if not content:
        return None

    # Clean
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    content = re.sub(r"[\t\f\v ]+", " ", content).strip()
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Normalize a few terms
    replacements = [
        (r"\bcrop?s\b", "crop"),
        (r"\bfarm(?:ing|er)?s?\b", "farming"),
        (r"\bpesticides?\b", "pesticide"),
        (r"\bfertilizer(?:s)?\b", "fertilizer"),
        (r"\birrigation\b", "irrigation"),
    ]
    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content, flags=re.IGNORECASE)

    if len(content) < 200:
        return None

    return {**rec, "content": content}


def process_with_spark(raw_jsonl: Path, processed_jsonl: Path) -> int:
    try:
        import importlib

        spark_sql = importlib.import_module("pyspark.sql")
        SparkSession = getattr(spark_sql, "SparkSession")
        F = importlib.import_module("pyspark.sql.functions")

        spark = (
            SparkSession.builder.appName("agri-rag-processing")
            .master("local[*]")
            .config("spark.sql.session.timeZone", "UTC")
            .getOrCreate()
        )

        df = spark.read.json(str(raw_jsonl))
        df = df.withColumn("content", F.regexp_replace(F.col("content"), r"\\s+", " "))

        df = df.withColumn(
            "content",
            F.regexp_replace(F.col("content"), r"(?i)\\bcrop?s\\b", "crop"),
        )
        df = df.withColumn(
            "content",
            F.regexp_replace(F.col("content"), r"(?i)\\bfarm(?:ing|er)?s?\\b", "farming"),
        )
        df = df.withColumn(
            "content",
            F.regexp_replace(F.col("content"), r"(?i)\\bpesticides?\\b", "pesticide"),
        )
        df = df.withColumn(
            "content",
            F.regexp_replace(F.col("content"), r"(?i)\\bfertilizer(?:s)?\\b", "fertilizer"),
        )

        df = df.withColumn("content", F.trim(F.col("content")))
        df = df.filter(F.length(F.col("content")) >= F.lit(200))

        df = df.withColumn(
            "content_hash",
            F.sha2(F.col("content"), 256),
        )
        df = df.dropDuplicates(["content_hash"]).drop("content_hash")

        processed_jsonl.parent.mkdir(parents=True, exist_ok=True)
        tmp_dir = processed_jsonl.parent / "_spark_out"
        if tmp_dir.exists():
            for p in tmp_dir.glob("*"):
                if p.is_file():
                    p.unlink()
        df.coalesce(1).write.mode("overwrite").json(str(tmp_dir))

        # Merge part file into target jsonl
        part_files = list(tmp_dir.glob("part-*.json"))
        if not part_files:
            spark.stop()
            return 0

        count = 0
        with processed_jsonl.open("w", encoding="utf-8") as out:
            for part in part_files:
                for line in part.read_text(encoding="utf-8").splitlines():
                    out.write(line + "\n")
                    count += 1

        spark.stop()
        return count

    except Exception:
        # Spark not available -> caller should use python fallback.
        raise


def process_fallback_python(raw_jsonl: Path, processed_jsonl: Path) -> int:
    processed_jsonl.parent.mkdir(parents=True, exist_ok=True)

    seen_hashes: set[str] = set()
    kept = 0
    with raw_jsonl.open("r", encoding="utf-8") as f_in, processed_jsonl.open("w", encoding="utf-8") as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            rec = _python_process_record(rec)
            if not rec:
                continue
            h = hashlib.sha256((rec.get("content") or "").encode("utf-8")).hexdigest()
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            kept += 1
    return kept


async def ingest_processed(processed_jsonl: Path, topic: str, max_docs: int | None) -> tuple[int, int]:
    service = IngestService()
    ingested_docs = 0
    total_chunks = 0

    try:
        with processed_jsonl.open("r", encoding="utf-8") as f:
            for line in f:
                if max_docs is not None and ingested_docs >= max_docs:
                    break
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                text = rec.get("content") or ""
                url = rec.get("url") or rec.get("source") or "manual"
                title = rec.get("title") or None
                document_type = rec.get("document_type") or "webpage"

                result = await service.ingest_text(
                    text=text,
                    title=title,
                    source=url,
                    topic=topic,
                    document_type=document_type,
                    preprocessed=True,
                )
                ingested_docs += 1
                total_chunks += int(result.get("chunks_created", 0))
    finally:
        await service.close()

    return ingested_docs, total_chunks


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="scripts/sources.json")
    parser.add_argument("--out-dir", type=str, default="data")
    parser.add_argument("--max-urls", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--topic", type=str, default="general")
    parser.add_argument("--no-spark", action="store_true")
    parser.add_argument("--max-docs", type=int, default=None)
    args = parser.parse_args()

    config_path = Path(args.config)
    out_dir = Path(args.out_dir)

    urls_txt = out_dir / "urls.txt"
    raw_jsonl = out_dir / "raw_pages.jsonl"
    processed_jsonl = out_dir / "processed_pages.jsonl"

    urls = await collect_urls(config_path, args.max_urls)
    urls_txt.parent.mkdir(parents=True, exist_ok=True)
    urls_txt.write_text("\n".join(urls) + "\n", encoding="utf-8")
    print(f"Collected {len(urls)} URLs -> {urls_txt}")

    scraped = await scrape_urls(urls, raw_jsonl, concurrency=args.concurrency)
    print(f"Scraped {scraped} pages -> {raw_jsonl}")

    processed = 0
    if args.no_spark:
        processed = process_fallback_python(raw_jsonl, processed_jsonl)
        print(f"Processed (python fallback) {processed} records -> {processed_jsonl}")
    else:
        try:
            processed = process_with_spark(raw_jsonl, processed_jsonl)
            print(f"Processed (spark) {processed} records -> {processed_jsonl}")
        except Exception as e:
            print(f"Spark processing failed ({e}). Re-run with --no-spark or install Java + pyspark.")
            raise

    docs, chunks = await ingest_processed(processed_jsonl, topic=args.topic, max_docs=args.max_docs)
    print(f"Ingested {docs} documents into Chroma ({chunks} chunks)")


if __name__ == "__main__":
    asyncio.run(main())
