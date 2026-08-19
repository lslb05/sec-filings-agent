from agente_filings_sec.citacoes import citacao_valida


def test_citacao_exata_e_valida() -> None:
    assert citacao_valida("risco de mercado", "Há um risco de mercado relevante.")


def test_citacao_com_espaco_e_caixa_diferentes_ainda_e_valida() -> None:
    assert citacao_valida("Risco   de\nMercado", "há um risco de mercado relevante")


def test_citacao_que_nao_aparece_no_texto_e_invalida() -> None:
    assert not citacao_valida("risco cambial", "Há um risco de mercado relevante.")


def test_citacao_vazia_e_invalida() -> None:
    assert not citacao_valida("   ", "qualquer texto")
