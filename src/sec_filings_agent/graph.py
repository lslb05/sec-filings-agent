"""LangGraph graph: fetches both filings, compares, verifies citations,
retries if needed.

The comparison node calls the LLM; the verification node doesn't — it's pure
Python checking substrings. It's the conditional edge between the two that
makes the graph worth it over a single function call: if a citation doesn't
match the source text, the state goes back to the comparison node with
specific feedback about what failed, up to a retry limit.
"""

from typing import Any, Literal, TypedDict

import httpx
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from sec_filings_agent.citations import is_valid_citation
from sec_filings_agent.extractor import extract_item_1a, html_to_text
from sec_filings_agent.llm import LLMClient
from sec_filings_agent.sources.edgar import fetch_10k

ATTEMPT_LIMIT = 3


class Change(TypedDict):
    type: Literal["added", "removed", "changed"]
    summary: str
    citation: str
    filing: Literal["old", "new"]


class State(TypedDict):
    ticker: str
    old_year: int
    new_year: int
    old_text: str
    new_text: str
    changes: list[Change]
    attempt: int
    invalid_citations: list[str]


def initial_state(*, ticker: str, old_year: int, new_year: int) -> State:
    return State(
        ticker=ticker,
        old_year=old_year,
        new_year=new_year,
        old_text="",
        new_text="",
        changes=[],
        attempt=0,
        invalid_citations=[],
    )


def build_graph(
    *, llm_client: LLMClient, http_client: httpx.Client
) -> CompiledStateGraph[State, None, State, State]:
    def fetch_old_filing_node(state: State) -> dict[str, Any]:
        html = fetch_10k(state["ticker"], state["old_year"], client=http_client)
        return {"old_text": extract_item_1a(html_to_text(html))}

    def fetch_new_filing_node(state: State) -> dict[str, Any]:
        html = fetch_10k(state["ticker"], state["new_year"], client=http_client)
        return {"new_text": extract_item_1a(html_to_text(html))}

    def compare_node(state: State) -> dict[str, Any]:
        raw_changes = llm_client.compare(
            old_text=state["old_text"],
            new_text=state["new_text"],
            feedback=state["invalid_citations"],
        )
        changes: list[Change] = [
            Change(type=c.type, summary=c.summary, citation=c.citation, filing=c.filing)
            for c in raw_changes
        ]
        return {"changes": changes, "attempt": state["attempt"] + 1}

    def verify_citations_node(state: State) -> dict[str, Any]:
        texts = {"old": state["old_text"], "new": state["new_text"]}
        invalid = [
            change["citation"]
            for change in state["changes"]
            if not is_valid_citation(change["citation"], texts[change["filing"]])
        ]
        return {"invalid_citations": invalid}

    def decide_after_verification(state: State) -> str:
        if not state["invalid_citations"]:
            return "done"
        if state["attempt"] >= ATTEMPT_LIMIT:
            return "done"
        return "retry"

    graph = StateGraph(State)
    graph.add_node("fetch_old_filing", fetch_old_filing_node)
    graph.add_node("fetch_new_filing", fetch_new_filing_node)
    graph.add_node("compare", compare_node)
    graph.add_node("verify_citations", verify_citations_node)

    graph.set_entry_point("fetch_old_filing")
    graph.add_edge("fetch_old_filing", "fetch_new_filing")
    graph.add_edge("fetch_new_filing", "compare")
    graph.add_edge("compare", "verify_citations")
    graph.add_conditional_edges(
        "verify_citations",
        decide_after_verification,
        {"retry": "compare", "done": END},
    )
    return graph.compile()
