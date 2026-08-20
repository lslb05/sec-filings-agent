# Project contract — SEC Filings Agent

Read the global `CLAUDE.md` and use this file for what's specific to this
repository.

## Product outcome

- **Problem:** comparing how a company's "Item 1A Risk Factors" changed
  from one 10-K to the next is manual analyst work. An agent that does this
  and cites its source proves RAG with verifiable grounding, not a summary
  that might be making things up.
- **User:** me, and whoever reviews the portfolio evaluating LLM/LangGraph
  fluency.
- **Verifiable output:** a list of changes (added/removed/changed) between
  the Item 1A of two 10-Ks from the same company, each item with a short
  citation that must appear literally in the corresponding source text.
- **Allowed data source:** SEC EDGAR — `data.sec.gov/submissions` (filing
  list by CIK) and `sec.gov/Archives` (the 10-K document), no credentials,
  just a descriptive `User-Agent`.
- **Smallest end-to-end cut:** a CLI that takes a ticker plus two years,
  runs the LangGraph graph, prints the list of changes with citation and
  source filing.
- **Out of scope:** more than 2 filings at a time, sections beyond Item 1A,
  vectorization/embeddings, a UI, production LLM cost observability.

Do not implement while a `FILL_IN` that changes the design is still open.

## Commands

```bash
uv sync
uv run python scripts/format.py
uv run python scripts/check.py
```

## Local rules

- The package is `sec_filings_agent` and lives in `src/sec_filings_agent`.
- Notebooks import from `src/`; production code never imports a notebook.
- Configuration comes from the environment via `Settings`.
- Preserve raw data and time-vintage metadata whenever there's ingestion.
- Update this file when a structural decision changes.

## Style

Public code, read by people. The rule is restraint — the full list is in
`AGENTS.md`, "Style" section, and applies equally to me and to Codex.

- A comment explains *why*, never *what*. If it paraphrases the line below,
  delete it; if the line needs paraphrasing, rename the variable instead.
- Docstrings only where the signature isn't enough (unit, timezone, side
  effect, what it raises). A three-line private helper doesn't need one.
- Tests assert behavior that can break, not a constant. Coverage is a
  consequence of testing what matters, never a target to inflate.
- Don't catch an exception you don't know how to handle; don't abstract for
  a single caller.

## Commit authorship

Author and committer are one and the same: the repository owner. No
`Co-Authored-By:`, no session trailer, no mention of Claude, Codex or any
tool. Don't change `user.name` or `user.email`.

## Session state

- **Decided:** first cut delivered — a LangGraph graph (fetches both
  filings, compares via LLM with tool-calling, verifies citations
  deterministically, retries with feedback if a citation fails, up to 3
  attempts). Item 1A extraction validated against real 10-Ks from AAPL,
  MSFT, and TSLA after three fixes (see `docs/decisions.md`).
- **Decided:** `LLMClient` is a one-method `Protocol`; `AnthropicClient` and
  `OpenAIClient` (`src/sec_filings_agent/llm.py`) implement the same
  contract against Anthropic's tool-calling and OpenAI's function-calling.
  `build_client()` picks which to instantiate from
  `SEC_FILINGS_AGENT_LLM_PROVIDER` (`anthropic` default, or `openai`) —
  only the chosen provider's key needs to be set. `graph.py` and `cli.py`
  don't know which concrete class is behind the `Protocol`.
- **Pending:** never run against the real Anthropic or OpenAI API — no
  `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in this environment. The
  `compare` node and the retry loop only have coverage with a deterministic
  fake LLM, for both providers.
- **Next step:** with a real key (from either provider), run `compare` for
  real against a pair of real 10-Ks and check whether the citations the
  model produces pass verification on the first attempt or whether the
  correction loop is actually needed in practice.
