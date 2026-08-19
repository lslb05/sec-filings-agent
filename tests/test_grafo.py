import json
from collections.abc import Callable

import httpx
import pytest

from agente_filings_sec.grafo import LIMITE_TENTATIVAS, construir_grafo, estado_inicial
from agente_filings_sec.llm import MudancaBruta

CriaClienteMock = Callable[[dict[str, httpx.Response]], httpx.Client]

_MAPA_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSOES_URL = "https://data.sec.gov/submissions/CIK0000320193.json"
_ACCESSION_ANTIGO = "0000000000-00-000000"
_ACCESSION_NOVO = "0000000000-00-000001"
_DOC_ANTIGO_URL = (
    "https://www.sec.gov/Archives/edgar/data/320193/"
    f"{_ACCESSION_ANTIGO.replace('-', '')}/antigo.htm"
)
_DOC_NOVO_URL = (
    "https://www.sec.gov/Archives/edgar/data/320193/"
    f"{_ACCESSION_NOVO.replace('-', '')}/novo.htm"
)

_TEXTO_ANTIGO = "Risco de mercado pode afetar nossos resultados. " * 20
_TEXTO_NOVO = _TEXTO_ANTIGO + "Também há um risco cibernético crescente na operação."


def _html_filing(texto_risco: str) -> str:
    return (
        f"<html><body>Item 1A Risk Factors {texto_risco} Item 1B Comments</body></html>"
    )


class _ClienteLLMFalso:
    def __init__(self, respostas: list[list[MudancaBruta]]) -> None:
        self._respostas = iter(respostas)
        self.feedbacks_recebidos: list[list[str]] = []

    def comparar(
        self, *, texto_antigo: str, texto_novo: str, feedback: list[str]
    ) -> list[MudancaBruta]:
        self.feedbacks_recebidos.append(feedback)
        return next(self._respostas)


@pytest.fixture
def cliente_http(criar_cliente_mock: CriaClienteMock) -> httpx.Client:
    mapa_tickers = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
    submissoes = {
        "filings": {
            "recent": {
                "form": ["10-K", "10-K"],
                "filingDate": ["2024-11-01", "2023-11-03"],
                "accessionNumber": [_ACCESSION_NOVO, _ACCESSION_ANTIGO],
                "primaryDocument": ["novo.htm", "antigo.htm"],
            }
        }
    }

    return criar_cliente_mock(
        {
            _MAPA_TICKERS_URL: httpx.Response(
                200, content=json.dumps(mapa_tickers).encode()
            ),
            _SUBMISSOES_URL: httpx.Response(
                200, content=json.dumps(submissoes).encode()
            ),
            _DOC_ANTIGO_URL: httpx.Response(200, text=_html_filing(_TEXTO_ANTIGO)),
            _DOC_NOVO_URL: httpx.Response(200, text=_html_filing(_TEXTO_NOVO)),
        }
    )


def test_citacao_invalida_aciona_nova_tentativa_que_corrige(
    cliente_http: httpx.Client,
) -> None:
    cliente_llm = _ClienteLLMFalso(
        [
            [
                MudancaBruta(
                    tipo="novo",
                    resumo="risco novo",
                    citacao="citação que não existe em nenhum dos dois textos",
                    filing="novo",
                )
            ],
            [
                MudancaBruta(
                    tipo="novo",
                    resumo="risco cibernético adicionado",
                    citacao="risco cibernético crescente",
                    filing="novo",
                )
            ],
        ]
    )
    grafo = construir_grafo(cliente_llm=cliente_llm, cliente_http=cliente_http)

    resultado = grafo.invoke(
        estado_inicial(ticker="AAPL", ano_antigo=2023, ano_novo=2024)
    )

    assert resultado["tentativa"] == 2
    assert resultado["citacoes_invalidas"] == []
    assert resultado["mudancas"][0]["citacao"] == "risco cibernético crescente"
    # A segunda chamada recebeu o feedback da citação que falhou na primeira.
    assert cliente_llm.feedbacks_recebidos[1] != []


def test_citacao_sempre_invalida_para_no_limite_de_tentativas(
    cliente_http: httpx.Client,
) -> None:
    resposta_invalida = [
        MudancaBruta(
            tipo="novo",
            resumo="x",
            citacao="isso nunca vai aparecer no texto",
            filing="novo",
        )
    ]
    cliente_llm = _ClienteLLMFalso([resposta_invalida] * LIMITE_TENTATIVAS)
    grafo = construir_grafo(cliente_llm=cliente_llm, cliente_http=cliente_http)

    resultado = grafo.invoke(
        estado_inicial(ticker="AAPL", ano_antigo=2023, ano_novo=2024)
    )

    assert resultado["tentativa"] == LIMITE_TENTATIVAS
    assert resultado["citacoes_invalidas"] != []


def test_sem_mudancas_encontradas_termina_na_primeira_tentativa(
    cliente_http: httpx.Client,
) -> None:
    cliente_llm = _ClienteLLMFalso([[]])
    grafo = construir_grafo(cliente_llm=cliente_llm, cliente_http=cliente_http)

    resultado = grafo.invoke(
        estado_inicial(ticker="AAPL", ano_antigo=2023, ano_novo=2024)
    )

    assert resultado["tentativa"] == 1
    assert resultado["mudancas"] == []
    assert resultado["citacoes_invalidas"] == []
