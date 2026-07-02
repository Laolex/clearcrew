import os

# Qwen Cloud (Model Studio / DashScope) — OpenAI-compatible international endpoint
BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)
API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

# Qwen3.7-Max for reasoning-heavy roles (compliance/treasury/negotiation),
# Qwen3.7-Plus for cheap per-payout calls (intake triage, audit explanations)
MODEL_STRONG = os.environ.get("CLEARCREW_MODEL_STRONG", "qwen3.7-max")
MODEL_FAST = os.environ.get("CLEARCREW_MODEL_FAST", "qwen3.7-plus")

EVENT_LOG_PATH = os.environ.get("CLEARCREW_EVENT_LOG", "events.jsonl")

# LLM call resilience: SDK-level timeout + retry-with-backoff on transient faults
REQUEST_TIMEOUT = float(os.environ.get("CLEARCREW_REQUEST_TIMEOUT", "120"))
MAX_RETRIES = int(os.environ.get("CLEARCREW_MAX_RETRIES", "3"))
