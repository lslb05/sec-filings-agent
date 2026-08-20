import json

import httpx
import pytest

from sec_filings_agent.cli import main
from sec_filings_agent.llm import RawChange

_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0000320193.json"
_ACCESSION_OLD = "0000000000-00-000000"
_ACCESSION_NEW = "0000000000-00-000001"
_DOC_OLD_URL = (
    f"https://www.sec.gov/Archives/edgar/data/320193/"
    f"{_ACCESSION_OLD.replace('-', '')}/old.htm"
)
_DOC_NEW_URL = (
    f"https://www.sec.gov/Archives/edgar/data/320193/"
    f"{_ACCESSION_NEW.replace('-', '')}/new.htm"
)

_TEXT = "Market risk may affect our results. " * 20


def _filing_html() -> str:
    return f"<html><body>Item 1A Risk Factors {_TEXT} Item 1B Comments</body></html>"


@pytest.fixture(autouse=True)
def key_in_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEC_FILINGS_AGENT_ANTHROPIC_API_KEY", "test-key")


def test_missing_key_guides_and_exits_with_code_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SEC_FILINGS_AGENT_ANTHROPIC_API_KEY", raising=False)

    assert (
        main(
            [
                "compare",
                "--ticker",
                "AAPL",
                "--old-year",
                "2023",
                "--new-year",
                "2024",
            ]
        )
        == 2
    )


def test_compare_prints_the_changes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ticker_map = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
    submissions = {
        "filings": {
            "recent": {
                "form": ["10-K", "10-K"],
                "filingDate": ["2024-11-01", "2023-11-03"],
                "accessionNumber": [_ACCESSION_NEW, _ACCESSION_OLD],
                "primaryDocument": ["new.htm", "old.htm"],
            }
        }
    }
    responses = {
        _TICKER_MAP_URL: httpx.Response(200, content=json.dumps(ticker_map).encode()),
        _SUBMISSIONS_URL: httpx.Response(200, content=json.dumps(submissions).encode()),
        _DOC_OLD_URL: httpx.Response(200, text=_filing_html()),
        _DOC_NEW_URL: httpx.Response(200, text=_filing_html()),
    }

    def respond(request: httpx.Request) -> httpx.Response:
        return responses[str(request.url)]

    # Capture the real class before patching the attribute on the httpx
    # module — otherwise the lambda below would call itself (the patch hits
    # the whole module, not just the usage inside cli.py).
    real_client = httpx.Client
    monkeypatch.setattr(
        "sec_filings_agent.cli.httpx.Client",
        lambda **_: real_client(transport=httpx.MockTransport(respond)),
    )

    class _FakeLLMClient:
        def compare(
            self, *, old_text: str, new_text: str, feedback: list[str]
        ) -> list[RawChange]:
            return [
                RawChange(
                    type="added",
                    summary="market risk mentioned",
                    citation="Market risk may affect our results",
                    filing="new",
                )
            ]

    monkeypatch.setattr(
        "sec_filings_agent.cli.build_client", lambda **_: _FakeLLMClient()
    )

    code = main(
        ["compare", "--ticker", "AAPL", "--old-year", "2023", "--new-year", "2024"]
    )

    output = capsys.readouterr().out
    assert code == 0
    assert "type,filing,summary,citation" in output
    assert "market risk mentioned" in output
