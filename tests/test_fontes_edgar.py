import json
from collections.abc import Callable

import httpx
import pytest

from agente_filings_sec.fontes.edgar import FilingNaoEncontrado, buscar_10k, buscar_cik

CriaClienteMock = Callable[[dict[str, httpx.Response]], httpx.Client]

_MAPA_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSOES_URL = "https://data.sec.gov/submissions/CIK0000320193.json"
_DOCUMENTO_URL = (
    "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl.htm"
)

_MAPA_TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
}

_SUBMISSOES = {
    "filings": {
        "recent": {
            "form": ["10-K", "8-K", "10-K"],
            "filingDate": ["2024-11-01", "2024-08-01", "2023-11-03"],
            "accessionNumber": [
                "0000320193-24-000123",
                "0000320193-24-000099",
                "0000320193-23-000106",
            ],
            "primaryDocument": ["aapl.htm", "outro.htm", "aapl-2023.htm"],
        }
    }
}


def _resposta_json(corpo: object) -> httpx.Response:
    return httpx.Response(200, content=json.dumps(corpo).encode())


def test_buscar_cik_encontra_pelo_ticker(criar_cliente_mock: CriaClienteMock) -> None:
    cliente = criar_cliente_mock({_MAPA_TICKERS_URL: _resposta_json(_MAPA_TICKERS)})

    assert buscar_cik("aapl", cliente=cliente) == 320193


def test_buscar_cik_ticker_desconhecido_levanta_erro(
    criar_cliente_mock: CriaClienteMock,
) -> None:
    cliente = criar_cliente_mock({_MAPA_TICKERS_URL: _resposta_json(_MAPA_TICKERS)})

    with pytest.raises(FilingNaoEncontrado):
        buscar_cik("INEXISTENTE", cliente=cliente)


def test_buscar_10k_acha_o_10k_do_ano_pedido(
    criar_cliente_mock: CriaClienteMock,
) -> None:
    cliente = criar_cliente_mock(
        {
            _MAPA_TICKERS_URL: _resposta_json(_MAPA_TICKERS),
            _SUBMISSOES_URL: _resposta_json(_SUBMISSOES),
            _DOCUMENTO_URL: httpx.Response(200, text="<html>conteudo do 10-K</html>"),
        }
    )

    texto = buscar_10k("AAPL", 2024, cliente=cliente)

    assert "conteudo do 10-K" in texto


def test_buscar_10k_sem_filing_no_ano_levanta_erro(
    criar_cliente_mock: CriaClienteMock,
) -> None:
    cliente = criar_cliente_mock(
        {
            _MAPA_TICKERS_URL: _resposta_json(_MAPA_TICKERS),
            _SUBMISSOES_URL: _resposta_json(_SUBMISSOES),
        }
    )

    with pytest.raises(FilingNaoEncontrado):
        buscar_10k("AAPL", 2020, cliente=cliente)
