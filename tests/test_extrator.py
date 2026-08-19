import pytest

from agente_filings_sec.extrator import (
    SecaoNaoEncontrada,
    extrair_item_1a,
    html_para_texto,
)


def test_html_para_texto_colapsa_espaco_em_branco() -> None:
    html = "<html><body><p>Olá</p>\n\n<p>  mundo  </p></body></html>"

    assert html_para_texto(html) == "Olá mundo"


def test_extrai_a_ocorrencia_com_mais_texto_ate_o_proximo_item() -> None:
    # Simula: sumário (curto), cabeçalho real (texto longo), uma
    # cross-reference narrativa cedo no documento e outra depois — nenhuma
    # das duas tem "Risk Factors" logo depois de "Item 1A", ao contrário do
    # sumário e do cabeçalho real.
    conteudo_real = "Risco de mercado pode afetar nossos resultados. " * 50
    texto = (
        "Como discutido no Item 1A deste relatório sob o título Risk "
        "Factors, há riscos relevantes. "
        "Item 1A. Risk Factors ver página 12. "
        "Item 1B Unresolved Staff Comments. "
        f"Item 1A. Risk Factors {conteudo_real} "
        "Item 2 Properties. "
        "Para mais detalhes, ver Item 1A deste relatório sob o título Risk "
        "Factors."
    )

    secao = extrair_item_1a(texto)

    assert secao.startswith("Risco de mercado")
    assert "Item 1B" not in secao
    assert len(secao) > 500


def test_sem_ocorrencia_de_item_1a_levanta_erro() -> None:
    with pytest.raises(SecaoNaoEncontrada):
        extrair_item_1a("Item 1 Business. Item 2 Properties.")


def test_ocorrencias_todas_curtas_levantam_erro() -> None:
    texto = "Item 1A. Risk Factors ver página 12. Item 1B Unresolved Staff Comments."

    with pytest.raises(SecaoNaoEncontrada):
        extrair_item_1a(texto)


def test_cross_reference_sem_risk_factors_adjacente_e_ignorada() -> None:
    texto = "Como discutido no Item 1A deste relatório, há riscos relevantes."

    with pytest.raises(SecaoNaoEncontrada):
        extrair_item_1a(texto)
