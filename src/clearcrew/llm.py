"""Thin Qwen Cloud client with token accounting for the benchmark.

Transport faults (connection drops, rate limits, 5xx) are retried by the SDK
with backoff; malformed JSON from the model gets one re-ask before failing
loudly — a payout must never proceed on a half-parsed decision.
"""
import json
import threading

from openai import OpenAI

from . import config

_client: OpenAI | None = None
_client_lock = threading.Lock()


def _get_client() -> OpenAI:
    global _client
    with _client_lock:
        if _client is None:
            if not config.API_KEY:
                raise RuntimeError(
                    "DASHSCOPE_API_KEY is not set — required for agent/benchmark "
                    "runs (the replay UI works without it)"
                )
            _client = OpenAI(
                api_key=config.API_KEY,
                base_url=config.BASE_URL,
                timeout=config.REQUEST_TIMEOUT,
                max_retries=config.MAX_RETRIES,
            )
        return _client

usage_totals = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
_usage_lock = threading.Lock()


class ModelResponseError(RuntimeError):
    """The model returned unusable output after retries."""


def _call(system: str, user: str, model: str | None, json_mode: bool, think: bool) -> str:
    resp = _get_client().chat.completions.create(
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
    return resp.choices[0].message.content or ""


def complete(system: str, user: str, model: str | None = None,
             json_mode: bool = True, think: bool = True) -> dict | str:
    content = _call(system, user, model, json_mode, think)
    if not json_mode:
        return content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # one re-ask, then fail loudly rather than act on a garbled decision
        content = _call(system, user, model, json_mode, think)
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ModelResponseError(
                f"model returned invalid JSON twice: {content[:200]!r}"
            ) from exc
