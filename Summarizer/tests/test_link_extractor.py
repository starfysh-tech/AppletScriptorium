from __future__ import annotations

import json
from pathlib import Path

import pytest

from Summarizer.link_extractor import (
    LinkRecord,
    extract_links_from_eml,
    extract_links_from_html,
    run_cli,
)

SAMPLES_DIR = Path(__file__).parent.parent / "Samples"
FIXTURE_06 = {
    "eml": SAMPLES_DIR / "google-alert-sample-2025-10-06.eml",
    "html": SAMPLES_DIR / "google-alert-sample-2025-10-06.html",
    "json": SAMPLES_DIR / "google-alert-sample-2025-10-06-links.json",
}
FIXTURE_07 = {
    "eml": SAMPLES_DIR / "google-alert-sample-2025-10-07.eml",
    "html": SAMPLES_DIR / "google-alert-sample-2025-10-07.html",
    "json": SAMPLES_DIR / "google-alert-sample-2025-10-07-links.json",
}


def load_expected(json_path: Path) -> list[LinkRecord]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return [LinkRecord(**item) for item in data]


@pytest.mark.parametrize(
    "fixture",
    [FIXTURE_06, FIXTURE_07],
    ids=["oct-06", "oct-07"],
)
def test_extract_from_html_fixture(fixture: dict[str, Path]):
    html = fixture["html"].read_text(encoding="utf-8")
    expected = load_expected(fixture["json"])
    assert extract_links_from_html(html) == expected


@pytest.mark.parametrize(
    "fixture",
    [FIXTURE_06, FIXTURE_07],
    ids=["oct-06", "oct-07"],
)
def test_extract_from_eml_fixture(tmp_path: Path, fixture: dict[str, Path]):
    eml_copy = tmp_path / fixture["eml"].name
    eml_copy.write_bytes(fixture["eml"].read_bytes())
    expected = load_expected(fixture["json"])
    assert extract_links_from_eml(eml_copy) == expected


def test_cli_stdout_matches_expected_tsv(capsys: pytest.CaptureFixture[str]):
    run_cli([str(FIXTURE_06["html"])])
    captured = capsys.readouterr().out.strip().splitlines()
    expected = [record.as_tsv_row() for record in load_expected(FIXTURE_06["json"])]
    assert captured == expected


def test_cli_stdout_matches_expected_json(capsys: pytest.CaptureFixture[str]):
    run_cli([str(FIXTURE_06["html"]), "--format", "json"])
    captured = json.loads(capsys.readouterr().out)
    expected = [record.to_dict() for record in load_expected(FIXTURE_06["json"])]
    assert captured == expected
