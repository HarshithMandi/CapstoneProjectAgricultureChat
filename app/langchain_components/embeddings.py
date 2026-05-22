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
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        self._async_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
        )

        self._sync_client: Optional[httpx.Client] = None

    def _ensure_api_key(self) -> None:
        if not self.api_key:
            raise RuntimeError(
                "OpenRouter API key is not configured. Set OPENROUTER_API_KEY in your environment or .env file."
            )

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None:
            headers = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
            )
        return self._sync_client

    def _parse_embeddings_response(self, response: httpx.Response) -> list[list[float]]:
        """Parse OpenRouter /embeddings response.

        OpenRouter generally returns {"data": [{"embedding": [...]}, ...]}.
        Some error cases may still be JSON but not include `data`.
        """

        try:
            data = response.json()
        except Exception:
            raise RuntimeError(
                f"OpenRouter embeddings returned non-JSON (status={response.status_code}): {response.text[:500]}"
            )

        if not isinstance(data, dict) or "data" not in data:
            raise RuntimeError(
                f"OpenRouter embeddings returned unexpected payload (status={response.status_code}): {str(data)[:800]}"
            )

        items = data.get("data") or []
        embeddings: list[list[float]] = []
        for item in items:
            if isinstance(item, dict) and "embedding" in item:
                embeddings.append(item["embedding"])

        if len(embeddings) != len(items):
            raise RuntimeError(
                f"OpenRouter embeddings payload missing embeddings for some items (status={response.status_code})."
            )
        return embeddings

    def _batched(self, texts: list[str]) -> list[list[str]]:
        batch_size = int(getattr(settings, "EMBEDDINGS_BATCH_SIZE", 64))
        if batch_size <= 0:
            batch_size = 64
        return [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        self._ensure_api_key()
        client = self._get_sync_client()
        all_embeddings: list[list[float]] = []
        for batch in self._batched(list(texts)):
            response = client.post(
                "/embeddings",
                json={"model": self.model, "input": batch},
            )
            response.raise_for_status()
            all_embeddings.extend(self._parse_embeddings_response(response))
        return all_embeddings

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        self._ensure_api_key()
        all_embeddings: list[list[float]] = []
        for batch in self._batched(list(texts)):
            response = await self._async_client.post(
                "/embeddings",
                json={"model": self.model, "input": batch},
            )
            response.raise_for_status()
            all_embeddings.extend(self._parse_embeddings_response(response))
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        self._ensure_api_key()
        client = self._get_sync_client()
        response = client.post(
            "/embeddings",
            json={"model": self.model, "input": [text]},
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or "data" not in data or not data.get("data"):
            raise RuntimeError(
                f"OpenRouter embeddings returned unexpected payload (status={response.status_code}): {str(data)[:800]}"
            )
        return data["data"][0]["embedding"]

    async def aembed_query(self, text: str) -> List[float]:
        self._ensure_api_key()
        response = await self._async_client.post(
            "/embeddings",
            json={"model": self.model, "input": [text]},
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or "data" not in data or not data.get("data"):
            raise RuntimeError(
                f"OpenRouter embeddings returned unexpected payload (status={response.status_code}): {str(data)[:800]}"
            )
        return data["data"][0]["embedding"]

    async def close(self):
        await self._async_client.aclose()
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None