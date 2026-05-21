from __future__ import annotations

from typing import List, Optional

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
        self._async_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        self._sync_client: Optional[httpx.Client] = None

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._sync_client

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        client = self._get_sync_client()
        response = client.post(
            "/embeddings",
            json={"model": self.model, "input": texts},
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        response = await self._async_client.post(
            "/embeddings",
            json={"model": self.model, "input": texts},
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    def embed_query(self, text: str) -> List[float]:
        client = self._get_sync_client()
        response = client.post(
            "/embeddings",
            json={"model": self.model, "input": [text]},
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    async def aembed_query(self, text: str) -> List[float]:
        response = await self._async_client.post(
            "/embeddings",
            json={"model": self.model, "input": [text]},
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    async def close(self):
        await self._async_client.aclose()
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None