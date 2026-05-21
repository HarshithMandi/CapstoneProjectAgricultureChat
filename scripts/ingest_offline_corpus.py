"""Ingest a local offline agriculture corpus into Chroma.

Why:
  - Lets you build/expand your RAG DB without crawling.
  - If crawling fails later, the chatbot still has local context via Chroma persistence.

Supported inputs:
  - .txt, .md
  - .pdf (requires pypdf)

Usage:
  PYTHONPATH="$PWD" .venv/bin/python -u scripts/ingest_offline_corpus.py \
    --path data/offline_corpus \
    --topic general \
    --max-files 200

Notes:
  - Chroma persistence directory is controlled by `CHROMA_PERSIST_DIR` in .env.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.services.ingest_service import IngestService


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    import importlib
    import io

    pypdf = importlib.import_module("pypdf")
    PdfReader = getattr(pypdf, "PdfReader")

    reader = PdfReader(io.BytesIO(path.read_bytes()))
    parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            parts.append(page_text)
    return "\n\n".join(parts).strip()


def _iter_files(root: Path) -> list[Path]:
    exts = {".txt", ".md", ".pdf"}
    files: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return sorted(files)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, default="data/offline_corpus")
    parser.add_argument("--topic", type=str, default="general")
    parser.add_argument("--max-files", type=int, default=500)
    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        raise SystemExit(f"Offline corpus folder not found: {root}")

    files = _iter_files(root)[: max(args.max_files, 0)]
    print(f"Found {len(files)} files under {root}")

    ingest = IngestService()
    ingested_docs = 0
    ingested_chunks = 0

    try:
        for i, path in enumerate(files, start=1):
            suffix = path.suffix.lower()
            try:
                if suffix == ".pdf":
                    text = _read_pdf(path)
                else:
                    text = _read_text_file(path)

                if not text.strip():
                    continue

                result = await ingest.ingest_text(
                    text=text,
                    title=path.stem,
                    source=str(path),
                    topic=args.topic,
                    document_type="pdf" if suffix == ".pdf" else "text",
                    preprocessed=False,
                )
                ingested_docs += 1
                ingested_chunks += int(result.get("chunks_created", 0))

                if i % 10 == 0:
                    print(f"Progress: {i}/{len(files)} files, docs={ingested_docs}, chunks={ingested_chunks}")

            except Exception as e:
                print(f"Skip {path}: {e}")

    finally:
        await ingest.close()

    print(f"Done: ingested {ingested_docs} documents ({ingested_chunks} chunks)")


if __name__ == "__main__":
    asyncio.run(main())
