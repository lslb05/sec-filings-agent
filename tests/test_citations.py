from sec_filings_agent.citations import is_valid_citation


def test_exact_citation_is_valid() -> None:
    assert is_valid_citation("market risk", "There is a relevant market risk.")


def test_citation_with_different_whitespace_and_case_is_still_valid() -> None:
    assert is_valid_citation("Market   Risk", "there is a relevant market risk")


def test_citation_not_found_in_text_is_invalid() -> None:
    assert not is_valid_citation("currency risk", "There is a relevant market risk.")


def test_empty_citation_is_invalid() -> None:
    assert not is_valid_citation("   ", "any text")
