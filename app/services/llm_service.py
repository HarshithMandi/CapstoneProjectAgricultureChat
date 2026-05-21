import httpx
import json
from typing import Any
from app.core.config import settings
from app.core.exceptions import LLMError
from tenacity import retry, stop_after_attempt, wait_exponential


class LLMService:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.LLM_MODEL
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=30.0),
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise LLMError(f"LLM generation failed: {str(e)}")

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            stream_timeout = httpx.Timeout(connect=10.0, read=None, write=30.0, pool=30.0)
            async with self.client.stream(
                "POST",
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
                timeout=stream_timeout,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data:"):
                        continue

                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break

                    try:
                        payload = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    choices = payload.get("choices") or []
                    if not choices:
                        continue

                    delta = choices[0].get("delta") or {}
                    token = delta.get("content")
                    if token:
                        yield token
        except Exception as e:
            raise LLMError(f"LLM streaming failed: {str(e)}")

    async def generate_with_context(
        self,
        query: str,
        context: str,
        chat_history: list[dict] | None = None,
    ) -> str:
        from app.prompts.agriculture_assistant import AGRICULTURE_SYSTEM_PROMPT
        from app.langchain_components.chains import get_agriculture_prompt

        history_text = ""
        if chat_history:
            for msg in chat_history[-10:]:
                history_text += f"{msg['role']}: {msg['content']}\n"

        prompt = get_agriculture_prompt()
        formatted_prompt = prompt.format_prompt(
            context=context,
            chat_history=history_text or "No previous conversation.",
            input=query,
        ).to_string()

        return await self.generate(formatted_prompt, system_prompt=AGRICULTURE_SYSTEM_PROMPT)

    async def stream_generate_with_context(
        self,
        query: str,
        context: str,
        chat_history: list[dict] | None = None,
    ):
        from app.prompts.agriculture_assistant import AGRICULTURE_SYSTEM_PROMPT
        from app.langchain_components.chains import get_agriculture_prompt

        history_text = ""
        if chat_history:
            for msg in chat_history[-10:]:
                history_text += f"{msg['role']}: {msg['content']}\n"

        prompt = get_agriculture_prompt()
        formatted_prompt = prompt.format_prompt(
            context=context,
            chat_history=history_text or "No previous conversation.",
            input=query,
        ).to_string()

        async for token in self.stream_generate(formatted_prompt, system_prompt=AGRICULTURE_SYSTEM_PROMPT):
            yield token

    async def close(self):
        await self.client.aclose()