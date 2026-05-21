from typing import List
import httpx
from langchain_core.embeddings import Embeddings
from app.core.config import settings


class OpenRouterEmbeddings(Embeddings):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.EMBEDDING_MODEL
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError("Use aembed_documents for async embedding")

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        response = await self._client.post(
            "/embeddings",
            json={"model": self.model, "input": texts},
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    def embed_query(self, text: str) -> List[float]:
        raise NotImplementedError("Use aembed_query for async embedding")

    async def aembed_query(self, text: str) -> List[float]:
        response = await self._client.post(
            "/embeddings",
            json={"model": self.model, "input": [text]},
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    async def close(self):
        await self._client.aclose()