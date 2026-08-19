from agente_filings_sec.llm import MudancaBruta, _montar_prompt


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
