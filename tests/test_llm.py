import pytest

from sec_filings_agent.llm import (
    AnthropicClient,
    OpenAIClient,
    RawChange,
    _build_prompt,
    build_client,
)


def test_prompt_includes_both_texts() -> None:
    prompt = _build_prompt("old filing text", "new filing text", [])

    assert "old filing text" in prompt
    assert "new filing text" in prompt
    assert "previous attempt" not in prompt


def test_prompt_with_feedback_includes_the_failed_citations() -> None:
    prompt = _build_prompt("old", "new", ["citation that didn't match"])

    assert "citation that didn't match" in prompt
    assert "previous attempt" in prompt


def test_raw_change_validates_expected_fields() -> None:
    change = RawChange(
        type="changed",
        summary="the exposure limit changed",
        citation="passage",
        filing="old",
    )

    assert change.type == "changed"
    assert change.filing == "old"


def test_build_client_anthropic_without_key_raises() -> None:
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        build_client(
            provider="anthropic",
            anthropic_api_key=None,
            anthropic_model=None,
            openai_api_key="openai-key",
            openai_model=None,
        )


def test_build_client_openai_without_key_raises() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        build_client(
            provider="openai",
            anthropic_api_key="anthropic-key",
            anthropic_model=None,
            openai_api_key=None,
            openai_model=None,
        )


def test_build_client_picks_the_provider_class() -> None:
    anthropic_client = build_client(
        provider="anthropic",
        anthropic_api_key="key",
        anthropic_model=None,
        openai_api_key=None,
        openai_model=None,
    )
    openai_client = build_client(
        provider="openai",
        anthropic_api_key=None,
        anthropic_model=None,
        openai_api_key="key",
        openai_model="gpt-5.4-mini",
    )

    assert isinstance(anthropic_client, AnthropicClient)
    assert isinstance(openai_client, OpenAIClient)
