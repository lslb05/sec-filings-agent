"""SEC EDGAR access: ticker→CIK, filing list, and document download.

No credentials — the SEC's only requirement is a descriptive User-Agent
identifying who's accessing. Without one, the SEC responds 403.
"""

import httpx

_TICKER_MAP = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_ARCHIVE_FILE = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"

_TIMEOUT_S = 30.0
_ATTEMPTS = 3


class FilingNotFound(Exception):
    """A ticker with no known CIK, or no 10-K filed in the requested year."""


def fetch_cik(ticker: str, *, client: httpx.Client) -> int:
    response = _get(_TICKER_MAP, client)
    for entry in response.json().values():
        if entry["ticker"].upper() == ticker.upper():
            return int(entry["cik_str"])
    raise FilingNotFound(f"ticker '{ticker}' not found in the SEC's map")


def fetch_10k(ticker: str, year: int, *, client: httpx.Client) -> str:
    """Returns the HTML of `ticker`'s 10-K whose `filingDate` falls in `year`."""
    cik = fetch_cik(ticker, client=client)
    response = _get(_SUBMISSIONS.format(cik=cik), client)
    filings = response.json()["filings"]["recent"]

    for form, date, accession, document in zip(
        filings["form"],
        filings["filingDate"],
        filings["accessionNumber"],
        filings["primaryDocument"],
        strict=True,
    ):
        if form == "10-K" and date.startswith(str(year)):
            url = _ARCHIVE_FILE.format(
                cik=cik, accession=accession.replace("-", ""), document=document
            )
            return _get(url, client).text

    raise FilingNotFound(f"no 10-K for '{ticker}' filed in {year}")


def _get(url: str, client: httpx.Client) -> httpx.Response:
    last: Exception | None = None
    for _attempt in range(_ATTEMPTS):
        try:
            response = client.get(url, timeout=_TIMEOUT_S)
        except httpx.TransportError as error:
            last = error
        else:
            if response.status_code < 400:
                return response
            # A 4xx is our fault (wrong ticker/CIK/URL) — retrying won't fix it.
            if response.status_code < 500:
                raise FilingNotFound(f"SEC responded {response.status_code} for {url}")
            last = FilingNotFound(f"SEC responded {response.status_code}")
    raise FilingNotFound(f"SEC did not respond after {_ATTEMPTS} attempts") from last
