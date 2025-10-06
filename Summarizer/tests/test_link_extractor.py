from __future__ import annotations

from pathlib import Path

import pytest

from link_extractor import (
    DEFAULT_EML,
    DEFAULT_HTML,
    DEFAULT_LINKS_TSV,
    LinkRecord,
    extract_links_from_eml,
    extract_links_from_html,
)

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "Samples"
EXPECTED_LINKS = DEFAULT_LINKS_TSV


def read_expected() -> list[LinkRecord]:
    records: list[LinkRecord] = []
    for line in EXPECTED_LINKS.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        title, url = line.split("\t", 1)
        records.append(LinkRecord(title=title, url=url))
    return records


def test_extract_from_html_fixture():
    html = DEFAULT_HTML.read_text(encoding="utf-8")
    expected = read_expected()
    assert extract_links_from_html(html) == expected


def test_extract_from_eml_fixture(tmp_path: Path):
    eml_copy = tmp_path / DEFAULT_EML.name
    eml_copy.write_bytes(DEFAULT_EML.read_bytes())
    expected = read_expected()
    assert extract_links_from_eml(eml_copy) == expected


def test_cli_stdout_matches_expected(capsys: pytest.CaptureFixture[str]):
    from link_extractor import run_cli

    run_cli([str(DEFAULT_HTML)])
    captured = capsys.readouterr().out.strip().splitlines()
    expected = [record.as_tsv_row() for record in read_expected()]
    assert captured == expected
