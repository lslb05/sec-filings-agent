"""Command-line interface. Logic lives in the package; this only coordinates."""

import argparse
import sys

import httpx

from sec_filings_agent.config import Settings
from sec_filings_agent.extractor import SectionNotFound
from sec_filings_agent.graph import build_graph, initial_state
from sec_filings_agent.llm import build_client
from sec_filings_agent.sources.edgar import FilingNotFound


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="sec-filings-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compare = subparsers.add_parser(
        "compare", help="Item 1A changes between two 10-Ks of the same ticker"
    )
    compare.add_argument("--ticker", required=True)
    compare.add_argument("--old-year", required=True, type=int)
    compare.add_argument("--new-year", required=True, type=int)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    config = Settings()

    try:
        llm_client = build_client(
            provider=config.llm_provider,
            anthropic_api_key=config.anthropic_api_key,
            anthropic_model=config.anthropic_model,
            openai_api_key=config.openai_api_key,
            openai_model=config.openai_model,
        )
    except ValueError as error:
        print(
            f"{error} (SEC_FILINGS_AGENT_LLM_PROVIDER={config.llm_provider})",
            file=sys.stderr,
        )
        return 2

    with httpx.Client(headers={"User-Agent": config.edgar_user_agent}) as http_client:
        graph = build_graph(llm_client=llm_client, http_client=http_client)
        state = initial_state(
            ticker=args.ticker,
            old_year=args.old_year,
            new_year=args.new_year,
        )
        try:
            result = graph.invoke(state)
        except FilingNotFound as error:
            print(f"filing not found: {error}", file=sys.stderr)
            return 2
        except SectionNotFound as error:
            print(f"could not extract Item 1A: {error}", file=sys.stderr)
            return 2

    invalid_citations = result["invalid_citations"]
    if invalid_citations:
        print(
            f"warning: {len(invalid_citations)} citation(s) unverified "
            f"after {result['attempt']} attempt(s)",
            file=sys.stderr,
        )

    print("type,filing,summary,citation")
    for change in result["changes"]:
        summary = change["summary"].replace('"', "'")
        citation = change["citation"].replace('"', "'")
        print(f'{change["type"]},{change["filing"]},"{summary}","{citation}"')
    return 0
