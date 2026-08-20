# sec-filings-agent

LangGraph agent that compares the "Item 1A Risk Factors" section of two
10-Ks from the same company and lists what changed — each change citing a
passage that must appear, literally, in the source text.

## The problem

Comparing how a company's risk factors changed from one 10-K to the next is
manual analyst work: reading two long sections and finding what's new,
removed, or altered. An agent that does this fast is worthless if it
invents a change that isn't in the text — so each change's citation is
checked by literal match against the source filing before it makes it into
the final response. There's no "public ground truth" for RAG over filings;
the grounding IS the validation.

## Result

```console
$ uv run python -m sec_filings_agent compare --ticker AAPL --old-year 2023 --new-year 2024
type,filing,summary,citation
...
```

I haven't run this command end to end with a real key — this development
environment has neither `ANTHROPIC_API_KEY` nor `OPENAI_API_KEY` (see
Limitations). What **was** validated with real data: EDGAR search and Item
1A extraction against real 10-Ks from Apple, Microsoft, and Tesla — the
three different HTML formats broke the extraction heuristic at some point
during development, and the fixes are documented in `docs/decisions.md`
because they're worth understanding, not just fixing.

## Problem and scope

- **User:** me, and whoever reviews the portfolio evaluating LLM/LangGraph
  fluency.
- **Decision:** a list of changes (added/removed/changed) between the Item
  1A of two 10-Ks, each one with a citation verified against the source
  text.
- **Input:** SEC EDGAR — `data.sec.gov/submissions` and
  `www.sec.gov/files/company_tickers.json` (ticker→CIK map) and
  `sec.gov/Archives` (the document). No credentials, just a descriptive
  `User-Agent`.
- **Out of scope:** more than 2 filings at a time, sections beyond Item 1A,
  vectorization/embeddings, a UI, production LLM cost observability.

## Architecture

```
                    ┌─────────────────────┐
                    │  fetch_old_filing   │
                    └──────────┬───────────┘
                               ▼
                    ┌─────────────────────┐
                    │  fetch_new_filing   │
                    └──────────┬───────────┘
                               ▼
                    ┌─────────────────────┐
              ┌────▶│      compare        │  calls the LLM (tool-calling)
              │     └──────────┬───────────┘
              │                ▼
              │     ┌─────────────────────┐
              │     │  verify_citations   │  deterministic, no LLM
              │     └──────────┬───────────┘
              │                ▼
      invalid citation     valid citation
      and attempt < 3          │
              └────────────────┴──▶ done
```

Three decisions worth explaining:

**Tool-calling instead of free-text JSON.** Both Anthropic and OpenAI
validate the response's shape against a schema before returning it — there's
no "the model forgot a comma" left to handle here. The content is still
revalidated by Pydantic, because coming structured from the API doesn't
excuse validating at an external boundary.

**LLM provider is a configuration choice, not a code choice.** `LLMClient`
is a `Protocol` with a single method (`compare`); `AnthropicClient` and
`OpenAIClient` implement the same contract against different tool-calling
APIs, and `build_client()` picks which to instantiate from
`SEC_FILINGS_AGENT_LLM_PROVIDER`. `graph.py` and `cli.py` only know the
`Protocol` — swapping providers doesn't change a line of either.

**The conditional edge is what separates this from a function with an
`if`.** `verify_citations` doesn't call the LLM — it's deterministic
substring matching. If a citation doesn't match the source text, the graph
goes back to the `compare` node with specific feedback about what failed, up
to 3 attempts. Actually tested (`tests/test_graph.py`): a fake LLM that gets
it wrong on the first attempt and right on the second, proving the loop and
the feedback work.

**Item 1A extraction needed two fixes after the initial design** — see the
next section and `docs/decisions.md`. That's not a footnote: it's this
project's real technical risk, more than the LLM itself.

## Run locally

Requirements: Python 3.12, `uv`, and an Anthropic **or** OpenAI key.

```bash
uv sync
cp .env.example .env      # fill in the chosen provider's key
uv run python -m sec_filings_agent compare --ticker AAPL --old-year 2023 --new-year 2024
```

`SEC_FILINGS_AGENT_LLM_PROVIDER` picks the provider (`anthropic`, default,
or `openai`) — only that provider's key needs to be filled in `.env`.
Without it, the command explains why and exits with code 2. If the filing
isn't found or Item 1A extraction fails, it also exits with code 2, with a
specific message — it never invents an answer.

## Quality

```bash
uv run python scripts/check.py
```

The check runs format, lint, types and tests with coverage. No test calls
the real Anthropic API, the OpenAI API, or the SEC — the LLM client and the
HTTP client are injected, and tests use fake/mocked versions.

## Structure

```text
src/sec_filings_agent/
    sources/edgar.py    ticker→CIK, filing list, download — no credentials
    extractor.py          Item 1A extraction heuristic (the real technical risk)
    citations.py           deterministic citation verification
    llm.py                  Anthropic and OpenAI clients via tool-calling, injectable interface
    graph.py                the LangGraph graph: fetch, compare, verify, retry
    cli.py                   coordination
```

## Limitations

- **Never validated against the real Anthropic or OpenAI API.** This
  development environment has neither `ANTHROPIC_API_KEY` nor
  `OPENAI_API_KEY`. `sources/edgar.py` and `extractor.py` were validated
  against real filings (AAPL, MSFT, TSLA); the `compare` node and the retry
  loop were only tested with a deterministic fake LLM.
- The Item 1A extraction heuristic was fixed twice during development
  against three different real-world formats — there's no guarantee it
  generalizes to every filer. A 10-K with atypical formatting could break it
  again; the behavior in that case is to fail with `SectionNotFound`, not
  return the wrong text.
- A 3-attempt limit for citation correction; if all fail, the output prints
  a warning and the unverified changes stay in the list — the caller
  decides whether to trust them.

## License

MIT. Third-party data keeps its own license and terms of use.
