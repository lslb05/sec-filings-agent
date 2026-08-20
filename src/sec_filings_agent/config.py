"""Application configuration loaded from environment variables."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings."""

    model_config = SettingsConfigDict(env_prefix="SEC_FILINGS_AGENT_", extra="ignore")

    log_level: str = "INFO"
    # Which provider builds the LLM client in cli.py — this only swaps the
    # implementation injected as LLMClient; graph.py doesn't know or need to.
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    anthropic_api_key: str | None = None
    anthropic_model: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    # The SEC requires a User-Agent identifying who's accessing; without a
    # descriptive one, access can be blocked. Override with your contact.
    edgar_user_agent: str = (
        "sec-filings-agent (portfolio project; no contact configured)"
    )
