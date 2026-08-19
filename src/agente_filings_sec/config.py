"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings."""

    model_config = SettingsConfigDict(env_prefix="AGENTE_FILINGS_SEC_", extra="ignore")

    log_level: str = "INFO"
    anthropic_api_key: str | None = None
    # A SEC exige um User-Agent que identifique quem está acessando; sem um
    # descritivo o acesso pode ser bloqueado. Sobrescreva com seu contato.
    edgar_user_agent: str = (
        "agente-filings-sec (projeto de portfólio; sem contato configurado)"
    )
