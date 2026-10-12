import pytest

from Summarizer import cli


@pytest.fixture(autouse=True)
def _isolated_status_log(tmp_path, monkeypatch):
    # Pipeline tests would otherwise append fake runs to the real runs/summarizer-status.log
    monkeypatch.setattr(cli, "STATUS_LOG", tmp_path / "summarizer-status.log")
