"""Async Anthropic client wrapper with image support and retries."""

from __future__ import annotations

import asyncio
from typing import Optional

import anthropic

# Models that removed the temperature parameter — passing it returns a 400.
NO_TEMPERATURE_MODELS = {"claude-opus-4-7"}


def _accepts_temperature(model: str) -> bool:
    return not any(model.startswith(m) for m in NO_TEMPERATURE_MODELS)


class AnthropicClient:
    """Sends moral-reasoning prompts to Claude with optional image attachment."""

    def __init__(self, model: str = "claude-opus-4-6", api_key: Optional[str] = None):
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

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
            content: list = [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": image_media_type, "data": image_b64},
                },
                {"type": "text", "text": user_text},
            ]
        else:
            content = user_text  # plain string is fine when no image

        kwargs = {
            "model": self.model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
        }
        if _accepts_temperature(self.model):
            kwargs["temperature"] = temperature

        last_error = "unknown"
        for attempt in range(retries + 1):
            try:
                resp = await asyncio.wait_for(
                    self._client.messages.create(**kwargs),
                    timeout=timeout,
                )
                if not resp.content:
                    last_error = "empty_content"
                    continue
                # First text block (skip thinking blocks if present)
                text = ""
                for block in resp.content:
                    if getattr(block, "type", "") == "text":
                        text = block.text.strip()
                        break
                if not text:
                    last_error = "no_text_block"
                    continue
                return {"response": text, "infra_error": None, "model": self.model}
            except asyncio.TimeoutError:
                last_error = "timeout"
            except anthropic.BadRequestError as e:
                # Don't retry 400s — schema/model issue, not transient.
                return {"response": "", "infra_error": f"bad_request:{str(e)[:200]}", "model": self.model}
            except Exception as e:
                last_error = f"{type(e).__name__}:{str(e)[:120]}"
            if attempt < retries:
                await asyncio.sleep(2 ** attempt)
        return {"response": "", "infra_error": last_error, "model": self.model}
