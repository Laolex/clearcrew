from types import SimpleNamespace

import pytest

from clearcrew import config, llm


@pytest.fixture
def runtime_env(monkeypatch):
    for name in ("CLEARCREW_PROVIDER", "DASHSCOPE_API_KEY", "OPENAI_API_KEY",
                 "CLEARCREW_MODEL_STRONG", "CLEARCREW_MODEL_FAST"):
        monkeypatch.delenv(name, raising=False)


def test_explicit_provider_wins_when_both_keys_are_set(runtime_env, monkeypatch):
    monkeypatch.setenv("CLEARCREW_PROVIDER", "openai")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dash-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    runtime = config.resolve_runtime()

    assert runtime.provider == "openai"
    assert runtime.api_key == "openai-key"
    assert runtime.base_url == "https://api.openai.com/v1"
    assert runtime.model_strong == "gpt-5.6-terra"
    assert runtime.model_fast == "gpt-5.6-luna"


def test_provider_is_inferred_from_the_only_available_key(runtime_env, monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dash-key")

    runtime = config.resolve_runtime()

    assert runtime.provider == "dashscope"
    assert runtime.api_key == "dash-key"
    assert runtime.model_strong == "qwen3.7-max"
    assert runtime.model_fast == "qwen3.7-plus"


def test_model_overrides_apply_to_the_active_provider(runtime_env, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("CLEARCREW_MODEL_STRONG", "gpt-5.6-sol")
    monkeypatch.setenv("CLEARCREW_MODEL_FAST", "gpt-5.6-sol")

    runtime = config.resolve_runtime()

    assert runtime.model_strong == "gpt-5.6-sol"
    assert runtime.model_fast == "gpt-5.6-sol"


@pytest.mark.parametrize(("keys", "message"), [
    ({"DASHSCOPE_API_KEY": "dash-key", "OPENAI_API_KEY": "openai-key"}, "both"),
    ({}, "neither"),
    ({"CLEARCREW_PROVIDER": "openai", "DASHSCOPE_API_KEY": "dash-key"}, "OPENAI_API_KEY"),
])
def test_provider_selection_rejects_ambiguous_or_missing_keys(runtime_env, monkeypatch, keys, message):
    for name, value in keys.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(RuntimeError, match=message):
        config.resolve_runtime()


@pytest.mark.parametrize("provider, expect_extra_body", [
    ("dashscope", {"enable_thinking": False}),
    ("openai", None),
])
def test_json_mode_works_for_both_providers_and_thinking_hack_is_dashscope_only(
        monkeypatch, provider, expect_extra_body):
    calls = []

    class Create:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=Create()))
    runtime = config.RuntimeConfig(
        provider=provider,
        provider_label=provider,
        api_key="key",
        base_url="https://example.test/v1",
        model_strong="strong",
        model_fast="fast",
    )
    monkeypatch.setattr(config, "resolve_runtime", lambda: runtime)
    monkeypatch.setattr(llm, "_get_client", lambda: fake_client)

    assert llm.complete("system", "user", think=False) == {"ok": True}
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == expect_extra_body
