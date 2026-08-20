import pytest

from agente_filings_sec.llm import (
    ClienteAnthropic,
    ClienteOpenAI,
    MudancaBruta,
    _montar_prompt,
    construir_cliente,
)


def test_prompt_inclui_os_dois_textos() -> None:
    prompt = _montar_prompt("texto do filing antigo", "texto do filing novo", [])

    assert "texto do filing antigo" in prompt
    assert "texto do filing novo" in prompt
    assert "tentativa anterior" not in prompt


def test_prompt_com_feedback_inclui_as_citacoes_que_falharam() -> None:
    prompt = _montar_prompt("antigo", "novo", ["citação que não bateu"])

    assert "citação que não bateu" in prompt
    assert "tentativa anterior" in prompt


def test_mudanca_bruta_valida_os_campos_esperados() -> None:
    mudanca = MudancaBruta(
        tipo="alterado",
        resumo="mudou o limite de exposição",
        citacao="trecho",
        filing="antigo",
    )

    assert mudanca.tipo == "alterado"
    assert mudanca.filing == "antigo"


def test_construir_cliente_anthropic_sem_chave_levanta() -> None:
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        construir_cliente(
            provedor="anthropic",
            anthropic_api_key=None,
            anthropic_modelo=None,
            openai_api_key="chave-openai",
            openai_modelo=None,
        )


def test_construir_cliente_openai_sem_chave_levanta() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        construir_cliente(
            provedor="openai",
            anthropic_api_key="chave-anthropic",
            anthropic_modelo=None,
            openai_api_key=None,
            openai_modelo=None,
        )


def test_construir_cliente_escolhe_a_classe_do_provedor() -> None:
    anthropic_cliente = construir_cliente(
        provedor="anthropic",
        anthropic_api_key="chave",
        anthropic_modelo=None,
        openai_api_key=None,
        openai_modelo=None,
    )
    openai_cliente = construir_cliente(
        provedor="openai",
        anthropic_api_key=None,
        anthropic_modelo=None,
        openai_api_key="chave",
        openai_modelo="gpt-5.4-mini",
    )

    assert isinstance(anthropic_cliente, ClienteAnthropic)
    assert isinstance(openai_cliente, ClienteOpenAI)
