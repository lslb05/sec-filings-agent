import pytest

from agente_filings_sec.config import Settings


def test_reads_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTE_FILINGS_SEC_LOG_LEVEL", "DEBUG")

    assert Settings().log_level == "DEBUG"
