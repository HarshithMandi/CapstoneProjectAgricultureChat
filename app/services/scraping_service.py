import httpx
import trafilatura
import io
import logging

from bs4 import BeautifulSoup
from readability import Document as ReadabilityDocument
from app.core.config import settings
from app.core.exceptions import IngestionError

logger = logging.getLogger(__name__)


class ScrapingService:
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "User-Agent": "AgriRAGBot/1.0 (+https://localhost; educational-project)",
            },
        )

    async def scrape_url(self, url: str) -> dict:
        try:
            await self._validate_url(url)
            response = await self.client.get(url, follow_redirects=True)
            response.raise_for_status()

            content_type = (response.headers.get("content-type") or "").lower()
            is_pdf = "application/pdf" in content_type or url.lower().endswith(".pdf")
            if is_pdf:
                return self._extract_from_pdf(response.content, source=url)

            content = response.text

            trafilatura_result = trafilatura.extract(
                content,
                include_links=False,
                include_images=False,
                output_format="json",
            )

            if trafilatura_result:
                import json
                extracted = json.loads(trafilatura_result)
                raw_text = (extracted.get("raw_text") or "").strip()
                title = (extracted.get("title") or "").strip()
                if raw_text:
                    return {
                        "content": raw_text,
                        "title": title,
                        "source": url,
                    }

            extracted = self._extract_with_readability(content)
            extracted.setdefault("source", url)
            extracted["content"] = (extracted.get("content") or "").strip()
            if not extracted["content"]:
                extracted = self._extract_with_bs4(content)
                extracted.setdefault("source", url)
            return extracted

        except Exception as e:
            msg = str(e) or e.__class__.__name__
            raise IngestionError(f"Failed to scrape URL {url}: {msg}")

    def _extract_from_pdf(self, pdf_bytes: bytes, source: str) -> dict:
        try:
            import importlib
            pypdf = importlib.import_module("pypdf")
            PdfReader = getattr(pypdf, "PdfReader")

            # Try normal read first, then fallback to a more permissive mode
            try:
                reader = PdfReader(io.BytesIO(pdf_bytes))
            except Exception as e:
                logger.debug("PdfReader initial parse failed, retrying with strict=False: %s", e)
                try:
                    # some pypdf versions accept strict=False to be more tolerant
                    reader = PdfReader(io.BytesIO(pdf_bytes), strict=False)  # type: ignore[arg-type]
                except Exception as e2:
                    logger.exception("Unable to parse PDF bytes from %s", source)
                    raise IngestionError(f"Failed to extract PDF text from {source}: {str(e2)}")

            parts: list[str] = []
            for page in getattr(reader, "pages", []) or []:
                try:
                    page_text = (page.extract_text() or "")
                except Exception:
                    # Best-effort: skip pages that fail to extract
                    logger.debug("Failed extracting text from a PDF page in %s", source)
                    page_text = ""
                if page_text.strip():
                    parts.append(page_text)

            content = "\n\n".join(parts).strip()
            return {
                "content": content,
                "title": "",
                "source": source,
            }
        except Exception as e:
            logger.exception("PDF extraction failed for %s", source)
            raise IngestionError(f"Failed to extract PDF text from {source}: {str(e)}")

    def extract_pdf_text(self, pdf_bytes: bytes, source: str) -> dict:
        return self._extract_from_pdf(pdf_bytes, source=source)

    async def _validate_url(self, url: str) -> None:
        if not url.startswith(("http://", "https://")):
            raise IngestionError(f"Invalid URL: {url}")

    def _extract_with_readability(self, html: str) -> dict:
        try:
            doc = ReadabilityDocument(html)
            title = doc.title() or ""
            summary = doc.summary() or ""

            soup = BeautifulSoup(summary, "html.parser")
            text = soup.get_text(separator="\n", strip=True)

            return {
                "content": text,
                "title": title,
            }
        except Exception:
            return self._extract_with_bs4(html)

    def _extract_with_bs4(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        for node in soup(["script", "style", "nav", "header", "footer", "aside"]):
            node.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return {
            "content": text,
            "title": "",
        }

    async def close(self):
        await self.client.aclose()