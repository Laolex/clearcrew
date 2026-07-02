"""Thin Qwen Cloud client with token accounting for the benchmark."""
import json
import threading

from openai import OpenAI

from . import config

_client = OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)

usage_totals = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
_usage_lock = threading.Lock()


def complete(system: str, user: str, model: str | None = None,
             json_mode: bool = True, think: bool = True) -> dict | str:
    resp = _client.chat.completions.create(
        model=model or config.MODEL_STRONG,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"} if json_mode else None,
        temperature=0.2,
        # triage/audit calls don't need chain-of-thought token spend
        extra_body=None if think else {"enable_thinking": False},
    )
    with _usage_lock:
        usage_totals["calls"] += 1
        if resp.usage:
            usage_totals["prompt_tokens"] += resp.usage.prompt_tokens
            usage_totals["completion_tokens"] += resp.usage.completion_tokens
    content = resp.choices[0].message.content or ""
    return json.loads(content) if json_mode else content
