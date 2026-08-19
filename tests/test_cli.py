import json

import httpx
import pytest

from agente_filings_sec.cli import main
from agente_filings_sec.llm import MudancaBruta

_MAPA_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSOES_URL = "https://data.sec.gov/submissions/CIK0000320193.json"
_ACCESSION_ANTIGO = "0000000000-00-000000"
_ACCESSION_NOVO = "0000000000-00-000001"
_DOC_ANTIGO_URL = (
    f"https://www.sec.gov/Archives/edgar/data/320193/"
    f"{_ACCESSION_ANTIGO.replace('-', '')}/antigo.htm"
)
_DOC_NOVO_URL = (
    f"https://www.sec.gov/Archives/edgar/data/320193/"
    f"{_ACCESSION_NOVO.replace('-', '')}/novo.htm"
)

_TEXTO = "Risco de mercado pode afetar nossos resultados. " * 20


def _html_filing() -> str:
    return f"<html><body>Item 1A Risk Factors {_TEXTO} Item 1B Comments</body></html>"


@pytest.fixture(autouse=True)
def chave_no_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTE_FILINGS_SEC_ANTHROPIC_API_KEY", "chave-de-teste")


def test_sem_chave_orienta_e_sai_com_codigo_dois(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENTE_FILINGS_SEC_ANTHROPIC_API_KEY", raising=False)

    assert (
        main(
            [
                "comparar",
                "--ticker",
                "AAPL",
                "--ano-antigo",
                "2023",
                "--ano-novo",
                "2024",
            ]
        )
        == 2
    )


def test_comparar_imprime_as_mudancas(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
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
    respostas = {
        _MAPA_TICKERS_URL: httpx.Response(
            200, content=json.dumps(mapa_tickers).encode()
        ),
        _SUBMISSOES_URL: httpx.Response(200, content=json.dumps(submissoes).encode()),
        _DOC_ANTIGO_URL: httpx.Response(200, text=_html_filing()),
        _DOC_NOVO_URL: httpx.Response(200, text=_html_filing()),
    }

    def responder(requisicao: httpx.Request) -> httpx.Response:
        return respostas[str(requisicao.url)]

    # Captura a classe real antes de remendar o atributo no módulo httpx —
    # senão o lambda abaixo chamaria a si mesmo (o patch atinge o módulo
    # inteiro, não só o uso dentro de cli.py).
    cliente_real = httpx.Client
    monkeypatch.setattr(
        "agente_filings_sec.cli.httpx.Client",
        lambda **_: cliente_real(transport=httpx.MockTransport(responder)),
    )

    class _ClienteLLMFalso:
        def comparar(
            self, *, texto_antigo: str, texto_novo: str, feedback: list[str]
        ) -> list[MudancaBruta]:
            return [
                MudancaBruta(
                    tipo="novo",
                    resumo="risco de mercado citado",
                    citacao="Risco de mercado pode afetar nossos resultados",
                    filing="novo",
                )
            ]

    monkeypatch.setattr(
        "agente_filings_sec.cli.ClienteAnthropic", lambda **_: _ClienteLLMFalso()
    )

    codigo = main(
        ["comparar", "--ticker", "AAPL", "--ano-antigo", "2023", "--ano-novo", "2024"]
    )

    saida = capsys.readouterr().out
    assert codigo == 0
    assert "tipo,filing,resumo,citacao" in saida
    assert "risco de mercado citado" in saida
