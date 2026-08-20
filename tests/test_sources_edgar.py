import json
from collections.abc import Callable

import httpx
import pytest

from sec_filings_agent.sources.edgar import FilingNotFound, fetch_10k, fetch_cik

MakeMockClient = Callable[[dict[str, httpx.Response]], httpx.Client]

_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0000320193.json"
_DOCUMENT_URL = (
    "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl.htm"
)

_TICKER_MAP = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
}

_SUBMISSIONS = {
    "filings": {
        "recent": {
            "form": ["10-K", "8-K", "10-K"],
            "filingDate": ["2024-11-01", "2024-08-01", "2023-11-03"],
            "accessionNumber": [
                "0000320193-24-000123",
                "0000320193-24-000099",
                "0000320193-23-000106",
            ],
            "primaryDocument": ["aapl.htm", "other.htm", "aapl-2023.htm"],
        }
    }
}


def _json_response(body: object) -> httpx.Response:
    return httpx.Response(200, content=json.dumps(body).encode())


def test_fetch_cik_finds_by_ticker(make_mock_client: MakeMockClient) -> None:
    client = make_mock_client({_TICKER_MAP_URL: _json_response(_TICKER_MAP)})

    assert fetch_cik("aapl", client=client) == 320193


def test_fetch_cik_unknown_ticker_raises(make_mock_client: MakeMockClient) -> None:
    client = make_mock_client({_TICKER_MAP_URL: _json_response(_TICKER_MAP)})

    with pytest.raises(FilingNotFound):
        fetch_cik("NONEXISTENT", client=client)


def test_fetch_10k_finds_the_10k_for_the_requested_year(
    make_mock_client: MakeMockClient,
) -> None:
    client = make_mock_client(
        {
            _TICKER_MAP_URL: _json_response(_TICKER_MAP),
            _SUBMISSIONS_URL: _json_response(_SUBMISSIONS),
            _DOCUMENT_URL: httpx.Response(200, text="<html>10-K content</html>"),
        }
    )

    text = fetch_10k("AAPL", 2024, client=client)

    assert "10-K content" in text


def test_fetch_10k_with_no_filing_in_the_year_raises(
    make_mock_client: MakeMockClient,
) -> None:
    client = make_mock_client(
        {
            _TICKER_MAP_URL: _json_response(_TICKER_MAP),
            _SUBMISSIONS_URL: _json_response(_SUBMISSIONS),
        }
    )

    with pytest.raises(FilingNotFound):
        fetch_10k("AAPL", 2020, client=client)
