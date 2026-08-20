# Decisions

Record only decisions that change the future cost of change.

## Template

### YYYY-MM-DD — Title

- **Context:** what constraint or problem required a decision.
- **Decision:** the path chosen.
- **Alternatives:** relevant options discarded.
- **Consequences:** gains, costs and the trigger to revisit.

### 2026-08-18 — Keep `CLAUDE.md` and `AGENTS.md` in the public repository

- **Context:** both files declare that the repository is built with agent
  support. The alternative was ignoring them in git so the public
  repository wouldn't reveal the workflow.
- **Decision:** keep both versioned and public.
- **Alternatives:** ignore `AGENTS.md` in `.gitignore`; keep it local only.
  Both break delegation to Codex, which reads this file from the
  repository — the cost is functional and immediate, the gain is cosmetic.
- **Consequences:** the repository states the method instead of hiding it,
  which is also verifiable by whoever reads it. Revisit if some destination
  ever requires the opposite.

### 2026-08-19 — Item 1A extraction: three versions to generalize

- **Context:** "Item 1A" appears several times in a 10-K — table of
  contents, narrative cross-reference, real heading — and the first
  heuristic ("the occurrence with the most text up to the next item
  marker") broke against a real Apple 10-K in two different ways before
  generalizing:
  1. A cross-reference inside the MD&A (which comes *after* the real Item
     1A/1B/2 in the document) had no "Item 1B"/"Item 2" after it — "the
     rest of the entire document" became a candidate and won on size.
  2. Fixed that, and a cross-reference *near the start* of the document
     (before the table of contents) had the real Item 1B much later in the
     text — the span stretched over the entire table of contents and the
     real section, still winning.
  3. Fixed to require "Risk Factors" right after "Item 1A" in the start
     marker (a narrative cross-reference never has that exact placement),
     Microsoft broke in a new way: their HTML splits the word "RISK" into
     "RIS K" mid-word (a rendering artifact), and the real heading repeats
     "PART I Item 1A" as a page header on every page of the section — dozens
     of "Item 1A" occurrences with no adjacent "Risk Factors", which no
     longer caused problems because they don't match the start marker.
- **Decision:** start marker = `item\s*1a\.?\s*ris\s?k\s*factors` (tolerates
  the broken "RIS K"); a candidate is only accepted if it has an end marker
  (`Item 1B`/`Item 2`) *actually found* — never "rest of the document" as a
  fallback; among the remaining candidates, the one with the largest span
  wins. Validated against real 10-Ks from Apple, Microsoft, and Tesla —
  three different HTML formats, all correct in the end.
- **Alternatives:** parsing the original HTML (not the already-flattened
  text) to use heading/bold structure as a signal — more robust in theory,
  but each filer uses different table/div HTML to format the same document;
  the textual signal ("Item 1A. Risk Factors" adjacent) generalized better
  in practice than trying to use formatting, which is exactly what varies
  most between different companies' 10-Ks.
- **Consequences:** the heuristic is textual, not structural — a filer with
  atypical formatting can still break it, and the behavior in that case is
  to fail with `SectionNotFound` (documented as a limitation), not silently
  return the wrong text. Revisit if a real filer breaks it again — the
  three cases documented here are the real bug history, not a hypothesis.
