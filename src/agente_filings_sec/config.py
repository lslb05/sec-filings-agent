"""Application configuration loaded from environment variables."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings."""

    model_config = SettingsConfigDict(env_prefix="AGENTE_FILINGS_SEC_", extra="ignore")

    log_level: str = "INFO"
    # Qual provedor monta o cliente LLM em cli.py — só troca a implementação
    # injetada em ClienteLLM; grafo.py não sabe nem precisa saber qual é.
    provedor_llm: Literal["anthropic", "openai"] = "anthropic"
    anthropic_api_key: str | None = None
    anthropic_modelo: str | None = None
    openai_api_key: str | None = None
    openai_modelo: str | None = None
    # A SEC exige um User-Agent que identifique quem está acessando; sem um
    # descritivo o acesso pode ser bloqueado. Sobrescreva com seu contato.
    edgar_user_agent: str = (
        "agente-filings-sec (projeto de portfólio; sem contato configurado)"
    )
