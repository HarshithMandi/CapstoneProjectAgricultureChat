import httpx
import trafilatura
import io

from bs4 import BeautifulSoup
from readability import Document as ReadabilityDocument
from app.core.config import settings
from app.core.exceptions import IngestionError


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

            reader = PdfReader(io.BytesIO(pdf_bytes))
            parts: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    parts.append(page_text)
            return {
                "content": "\n\n".join(parts).strip(),
                "title": "",
                "source": source,
            }
        except Exception as e:
            raise IngestionError(f"Failed to extract PDF text from {source}: {str(e)}")

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