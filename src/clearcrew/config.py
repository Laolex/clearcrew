import os

# Qwen Cloud (Model Studio / DashScope) — OpenAI-compatible international endpoint
BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)
API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

# qwen-max for reasoning-heavy roles, qwen-turbo for cheap triage
MODEL_STRONG = os.environ.get("CLEARCREW_MODEL_STRONG", "qwen-max")
MODEL_FAST = os.environ.get("CLEARCREW_MODEL_FAST", "qwen-turbo")

EVENT_LOG_PATH = os.environ.get("CLEARCREW_EVENT_LOG", "events.jsonl")
