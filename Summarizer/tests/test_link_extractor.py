from __future__ import annotations

import json
from pathlib import Path

import pytest

from link_extractor import (
    DEFAULT_EML,
    DEFAULT_HTML,
    DEFAULT_LINKS_JSON,
    LinkRecord,
    extract_links_from_eml,
    extract_links_from_html,
    run_cli,
)


def load_expected() -> list[LinkRecord]:
    data = json.loads(DEFAULT_LINKS_JSON.read_text(encoding="utf-8"))
    return [LinkRecord(**item) for item in data]


def test_extract_from_html_fixture():
    html = DEFAULT_HTML.read_text(encoding="utf-8")
    expected = load_expected()
    assert extract_links_from_html(html) == expected


def test_extract_from_eml_fixture(tmp_path: Path):
    eml_copy = tmp_path / DEFAULT_EML.name
    eml_copy.write_bytes(DEFAULT_EML.read_bytes())
    expected = load_expected()
    assert extract_links_from_eml(eml_copy) == expected


def test_cli_stdout_matches_expected_tsv(capsys: pytest.CaptureFixture[str]):
    run_cli([str(DEFAULT_HTML)])
    captured = capsys.readouterr().out.strip().splitlines()
    expected = [record.as_tsv_row() for record in load_expected()]
    assert captured == expected


def test_cli_stdout_matches_expected_json(capsys: pytest.CaptureFixture[str]):
    run_cli([str(DEFAULT_HTML), "--format", "json"])
    captured = json.loads(capsys.readouterr().out)
    expected = [record.to_dict() for record in load_expected()]
    assert captured == expected
