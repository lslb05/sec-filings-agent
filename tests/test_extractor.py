import pytest

from sec_filings_agent.extractor import SectionNotFound, extract_item_1a, html_to_text


def test_html_to_text_collapses_whitespace() -> None:
    html = "<html><body><p>Hello</p>\n\n<p>  world  </p></body></html>"

    assert html_to_text(html) == "Hello world"


def test_extracts_the_occurrence_with_the_most_text_up_to_the_next_item() -> None:
    # Simulates: table of contents (short), real heading (long text), one
    # narrative cross-reference early in the document and another later —
    # neither has "Risk Factors" right after "Item 1A", unlike the table of
    # contents and the real heading.
    real_content = "Market risk may affect our results. " * 50
    text = (
        "As discussed in Item 1A of this report under the heading Risk "
        "Factors, there are material risks. "
        "Item 1A. Risk Factors see page 12. "
        "Item 1B Unresolved Staff Comments. "
        f"Item 1A. Risk Factors {real_content} "
        "Item 2 Properties. "
        "For more details, see Item 1A of this report under the heading "
        "Risk Factors."
    )

    section = extract_item_1a(text)

    assert section.startswith("Market risk")
    assert "Item 1B" not in section
    assert len(section) > 500


def test_no_item_1a_occurrence_raises() -> None:
    with pytest.raises(SectionNotFound):
        extract_item_1a("Item 1 Business. Item 2 Properties.")


def test_all_short_occurrences_raise() -> None:
    text = "Item 1A. Risk Factors see page 12. Item 1B Unresolved Staff Comments."

    with pytest.raises(SectionNotFound):
        extract_item_1a(text)


def test_cross_reference_without_adjacent_risk_factors_is_ignored() -> None:
    text = "As discussed in Item 1A of this report, there are material risks."

    with pytest.raises(SectionNotFound):
        extract_item_1a(text)
