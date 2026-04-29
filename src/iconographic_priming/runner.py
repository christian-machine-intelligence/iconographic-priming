"""Per-call orchestration: cache check → image selection → API call → score."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from .cache import CallKey, cache_get, cache_put
from .clients.anthropic_client import AnthropicClient
from .clients.openai_client import OpenAIClient
from .images import ImageEntry, encode_image, select_image

ARMS = ("baseline", "neutral", "sacred")


@dataclass(frozen=True)
class CallSpec:
    """One call to run: a scenario + run + arm + model."""
    model_id: str
    arm: str  # "baseline" | "neutral" | "sacred"
    scenario_text: str
    target: str  # "A" or "B"
    virtue: str
    variant: str
    base_id: str
    run_index: int
    ab_seed: int
    system_prompt: str
    temperature: float


def select_image_for_arm(
    arm: str,
    *,
    sacred_bundle: list[ImageEntry],
    neutral_bundle: list[ImageEntry],
    base_id: str,
    run_index: int,
) -> Optional[ImageEntry]:
    if arm == "baseline":
        return None
    if arm == "neutral":
        return select_image(neutral_bundle, base_id=base_id, run_index=run_index)
    if arm == "sacred":
        return select_image(sacred_bundle, base_id=base_id, run_index=run_index)
    raise ValueError(f"Unknown arm: {arm}")


def parse_answer(response: str) -> Optional[str]:
    """Match VirtueBench-2's parse_answer: first standalone A or B."""
    text = response.strip()
    if len(text) >= 1 and text[0] in ("A", "B"):
        if len(text) == 1 or not text[1].isalpha():
            return text[0]
    return None


async def run_one_call(
    spec: CallSpec,
    *,
    client: Union[AnthropicClient, OpenAIClient],
    image: Optional[ImageEntry],
    cache_dir: Path,
    sem: asyncio.Semaphore,
) -> dict:
    """Run a single call (or fetch from cache). Returns the cached/new result dict."""
    key = CallKey(
        model=spec.model_id,
        scenario_text=spec.scenario_text,
        image_id=image.id if image else None,
        virtue=spec.virtue,
        variant=spec.variant,
        base_id=spec.base_id,
        run_index=spec.run_index,
        ab_seed=spec.ab_seed,
        system_prompt=spec.system_prompt,
        temperature=spec.temperature,
    )
    cached = cache_get(cache_dir, key)
    if cached is not None and "response" in cached:
        return {**cached, "from_cache": True}

    image_b64 = encode_image(str(image.file)) if image else None

    # Reasoning models (GPT-5.5, Opus 4.7 with adaptive thinking) need a much
    # bigger output budget — reasoning tokens are billed but invisible.
    is_reasoning = any(spec.model_id.startswith(m) for m in
                       ("claude-opus-4-7", "gpt-5", "o1", "o3", "o4"))
    max_tokens = 4096 if is_reasoning else 512

    async with sem:
        result = await client.query(
            system_prompt=spec.system_prompt,
            user_text=spec.scenario_text,
            image_b64=image_b64,
            image_media_type="image/jpeg",
            temperature=spec.temperature,
            max_tokens=max_tokens,
        )

    answer = parse_answer(result.get("response", "")) if not result.get("infra_error") else None
    correct = answer == spec.target if answer else None

    record = {
        "key_hash": key.hash(),
        "model": spec.model_id,
        "arm": spec.arm,
        "virtue": spec.virtue,
        "variant": spec.variant,
        "base_id": spec.base_id,
        "run_index": spec.run_index,
        "target": spec.target,
        "image_id": image.id if image else None,
        "response": result.get("response", ""),
        "infra_error": result.get("infra_error"),
        "model_answer": answer,
        "correct": correct,
        "temperature": spec.temperature,
    }
    cache_put(cache_dir, key, record)
    return {**record, "from_cache": False}
