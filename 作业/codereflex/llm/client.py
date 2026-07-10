from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    usage: dict[str, Any] = field(default_factory=dict)


class LLMClient:
    """OpenAI-compatible chat completion client."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    async def complete(self, messages: list[dict], model: str) -> LLMResponse:
        import httpx
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {"model": model, "messages": messages}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(3):
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in (429, 500, 502, 503):
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return LLMResponse(
                    text=data["choices"][0]["message"]["content"],
                    usage=data.get("usage", {}),
                )
            raise RuntimeError("LLM call failed after 3 retries")


class MockLLMClient:
    """Returns scripted responses in order, for deterministic offline tests."""

    def __init__(self, script: list[str]):
        self._script = list(script)
        self._index = 0

    async def complete(self, messages: list[dict], model: str) -> LLMResponse:
        if self._index >= len(self._script):
            raise RuntimeError("Mock script exhausted")
        text = self._script[self._index]
        self._index += 1
        return LLMResponse(text=text, usage={})
