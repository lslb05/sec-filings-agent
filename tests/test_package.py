import pytest

from sec_filings_agent.config import Settings


def test_reads_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEC_FILINGS_AGENT_LOG_LEVEL", "DEBUG")

    assert Settings().log_level == "DEBUG"
