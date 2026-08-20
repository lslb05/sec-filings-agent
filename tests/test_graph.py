import json
from collections.abc import Callable

import httpx
import pytest

from sec_filings_agent.graph import ATTEMPT_LIMIT, build_graph, initial_state
from sec_filings_agent.llm import RawChange

MakeMockClient = Callable[[dict[str, httpx.Response]], httpx.Client]

_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0000320193.json"
_ACCESSION_OLD = "0000000000-00-000000"
_ACCESSION_NEW = "0000000000-00-000001"
_DOC_OLD_URL = (
    "https://www.sec.gov/Archives/edgar/data/320193/"
    f"{_ACCESSION_OLD.replace('-', '')}/old.htm"
)
_DOC_NEW_URL = (
    "https://www.sec.gov/Archives/edgar/data/320193/"
    f"{_ACCESSION_NEW.replace('-', '')}/new.htm"
)

_OLD_TEXT = "Market risk may affect our results. " * 20
_NEW_TEXT = _OLD_TEXT + "There is also a growing cyber risk in operations."


def _filing_html(risk_text: str) -> str:
    return (
        f"<html><body>Item 1A Risk Factors {risk_text} Item 1B Comments</body></html>"
    )


class _FakeLLMClient:
    def __init__(self, responses: list[list[RawChange]]) -> None:
        self._responses = iter(responses)
        self.received_feedback: list[list[str]] = []

    def compare(
        self, *, old_text: str, new_text: str, feedback: list[str]
    ) -> list[RawChange]:
        self.received_feedback.append(feedback)
        return next(self._responses)


@pytest.fixture
def http_client(make_mock_client: MakeMockClient) -> httpx.Client:
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

    return make_mock_client(
        {
            _TICKER_MAP_URL: httpx.Response(
                200, content=json.dumps(ticker_map).encode()
            ),
            _SUBMISSIONS_URL: httpx.Response(
                200, content=json.dumps(submissions).encode()
            ),
            _DOC_OLD_URL: httpx.Response(200, text=_filing_html(_OLD_TEXT)),
            _DOC_NEW_URL: httpx.Response(200, text=_filing_html(_NEW_TEXT)),
        }
    )


def test_invalid_citation_triggers_a_retry_that_fixes_it(
    http_client: httpx.Client,
) -> None:
    llm_client = _FakeLLMClient(
        [
            [
                RawChange(
                    type="added",
                    summary="new risk",
                    citation="citation that doesn't exist in either text",
                    filing="new",
                )
            ],
            [
                RawChange(
                    type="added",
                    summary="cyber risk added",
                    citation="growing cyber risk",
                    filing="new",
                )
            ],
        ]
    )
    graph = build_graph(llm_client=llm_client, http_client=http_client)

    result = graph.invoke(initial_state(ticker="AAPL", old_year=2023, new_year=2024))

    assert result["attempt"] == 2
    assert result["invalid_citations"] == []
    assert result["changes"][0]["citation"] == "growing cyber risk"
    # The second call received feedback about the citation that failed the first time.
    assert llm_client.received_feedback[1] != []


def test_always_invalid_citation_stops_at_the_attempt_limit(
    http_client: httpx.Client,
) -> None:
    invalid_response = [
        RawChange(
            type="added",
            summary="x",
            citation="this will never appear in the text",
            filing="new",
        )
    ]
    llm_client = _FakeLLMClient([invalid_response] * ATTEMPT_LIMIT)
    graph = build_graph(llm_client=llm_client, http_client=http_client)

    result = graph.invoke(initial_state(ticker="AAPL", old_year=2023, new_year=2024))

    assert result["attempt"] == ATTEMPT_LIMIT
    assert result["invalid_citations"] != []


def test_no_changes_found_stops_on_the_first_attempt(
    http_client: httpx.Client,
) -> None:
    llm_client = _FakeLLMClient([[]])
    graph = build_graph(llm_client=llm_client, http_client=http_client)

    result = graph.invoke(initial_state(ticker="AAPL", old_year=2023, new_year=2024))

    assert result["attempt"] == 1
    assert result["changes"] == []
    assert result["invalid_citations"] == []
