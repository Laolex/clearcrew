"""Runtime configuration for ClearCrew's interchangeable model providers."""
import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class RuntimeConfig:
    provider: str
    provider_label: str
    api_key: str
    base_url: str
    model_strong: str
    model_fast: str


def resolve_runtime(environ: Mapping[str, str] | None = None) -> RuntimeConfig:
    """Resolve the active provider without guessing when credentials conflict."""
    env = os.environ if environ is None else environ
    explicit = env.get("CLEARCREW_PROVIDER", "").strip().lower()
    dashscope_key = env.get("DASHSCOPE_API_KEY", "")
    openai_key = env.get("OPENAI_API_KEY", "")

    if explicit:
        if explicit not in {"dashscope", "openai"}:
            raise RuntimeError(
                "CLEARCREW_PROVIDER must be 'dashscope' or 'openai'"
            )
        provider = explicit
    elif dashscope_key and openai_key:
        raise RuntimeError(
            "both DASHSCOPE_API_KEY and OPENAI_API_KEY are set; "
            "set CLEARCREW_PROVIDER explicitly"
        )
    elif dashscope_key:
        provider = "dashscope"
    elif openai_key:
        provider = "openai"
    else:
        raise RuntimeError(
            "neither DASHSCOPE_API_KEY nor OPENAI_API_KEY is set; "
            "set one key and optionally CLEARCREW_PROVIDER"
        )

    if provider == "dashscope":
        if not dashscope_key:
            raise RuntimeError(
                "DASHSCOPE_API_KEY is not set for CLEARCREW_PROVIDER=dashscope"
            )
        return RuntimeConfig(
            provider="dashscope",
            provider_label="Qwen Cloud (DashScope)",
            api_key=dashscope_key,
            base_url=env.get(
                "DASHSCOPE_BASE_URL",
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            ),
            model_strong=env.get("CLEARCREW_MODEL_STRONG", "qwen3.7-max"),
            model_fast=env.get("CLEARCREW_MODEL_FAST", "qwen3.7-plus"),
        )

    if not openai_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set for CLEARCREW_PROVIDER=openai"
        )
    return RuntimeConfig(
        provider="openai",
        provider_label="OpenAI",
        api_key=openai_key,
        base_url=env.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model_strong=env.get("CLEARCREW_MODEL_STRONG", "gpt-5.6-terra"),
        model_fast=env.get("CLEARCREW_MODEL_FAST", "gpt-5.6-luna"),
    )


EVENT_LOG_PATH = os.environ.get("CLEARCREW_EVENT_LOG", "events.jsonl")

# LLM call resilience: SDK-level timeout + retry-with-backoff on transient faults.
# The timeout must exceed the worst-case legitimate call: the monolith baseline
# reasons over an entire batch in ONE request (~140s at n=36).
REQUEST_TIMEOUT = float(os.environ.get("CLEARCREW_REQUEST_TIMEOUT", "300"))
MAX_RETRIES = int(os.environ.get("CLEARCREW_MAX_RETRIES", "3"))
