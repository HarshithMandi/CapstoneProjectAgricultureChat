import httpx
import trafilatura
from bs4 import BeautifulSoup
from readability import Document as ReadabilityDocument
from app.core.config import settings
from app.core.exceptions import IngestionError


class ScrapingService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def scrape_url(self, url: str) -> dict:
        try:
            await self._validate_url(url)
            response = await self.client.get(url, follow_redirects=True)
            response.raise_for_status()

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
                return {
                    "content": extracted.get("raw_text", ""),
                    "title": extracted.get("title", ""),
                    "source": url,
                }

            extracted = self._extract_with_readability(content)
            return extracted

        except Exception as e:
            raise IngestionError(f"Failed to scrape URL {url}: {str(e)}")

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
            soup = BeautifulSoup(html, "html.parser")
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()

            text = soup.get_text(separator="\n", strip=True)
            return {
                "content": text,
                "title": "",
            }

    async def close(self):
        await self.client.aclose()