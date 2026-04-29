"""Async OpenAI client wrapper with image support and retries."""

from __future__ import annotations

import asyncio
from typing import Optional

from openai import AsyncOpenAI, BadRequestError


def _is_reasoning_model(model: str) -> bool:
    return any(x in model for x in ["gpt-5", "o1", "o3", "o4"])


# Models that only accept the default temperature value — passing 0.7 returns a 400.
NO_TEMPERATURE_MODELS_PREFIXES = ("gpt-5.5", "o1", "o3", "o4")


def _accepts_temperature(model: str) -> bool:
    return not any(model.startswith(p) for p in NO_TEMPERATURE_MODELS_PREFIXES)


class OpenAIClient:
    """Sends moral-reasoning prompts to GPT with optional image attachment."""

    def __init__(self, model: str = "gpt-5.4", api_key: Optional[str] = None):
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key)

    async def query(
        self,
        *,
        system_prompt: str,
        user_text: str,
        image_b64: Optional[str] = None,
        image_media_type: str = "image/jpeg",
        temperature: float = 0.7,
        max_tokens: int = 200,
        retries: int = 3,
        timeout: int = 120,
    ) -> dict:
        """Returns {response: str, infra_error: str | None, model: str}."""
        if image_b64 is not None:
            data_url = f"data:{image_media_type};base64,{image_b64}"
            user_content: list = [
                {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                {"type": "text", "text": user_text},
            ]
        else:
            user_content = user_text

        kwargs: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        if _accepts_temperature(self.model):
            kwargs["temperature"] = temperature
        # GPT-5.x and o-series take max_completion_tokens; older models take max_tokens.
        # Reasoning tokens count as output, so give a generous cap.
        if _is_reasoning_model(self.model):
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens

        last_error = "unknown"
        for attempt in range(retries + 1):
            try:
                resp = await asyncio.wait_for(
                    self._client.chat.completions.create(**kwargs),
                    timeout=timeout,
                )
                text = resp.choices[0].message.content
                if not text:
                    last_error = "empty_content"
                    continue
                return {"response": text.strip(), "infra_error": None, "model": self.model}
            except asyncio.TimeoutError:
                last_error = "timeout"
            except BadRequestError as e:
                return {"response": "", "infra_error": f"bad_request:{str(e)[:200]}", "model": self.model}
            except Exception as e:
                last_error = f"{type(e).__name__}:{str(e)[:120]}"
            if attempt < retries:
                await asyncio.sleep(2 ** attempt)
        return {"response": "", "infra_error": last_error, "model": self.model}
