"""Tests for the model-evaluation metrics and runner helpers."""

import pytest

from Summarizer.evals.gold_standard import GoldAnnotation
from Summarizer.evals.metrics import detect_hallucinations, evaluate_accuracy, evaluate_consistency
from Summarizer.evals.runner import ModelResults

ARTICLE = (
    "A cross-sectional survey of 1,275 adults with cardiovascular risk factors found that "
    "medication confidence predicted emergency department visits (p<0.001). The authors note "
    "the sample was drawn from a single health system, limiting generalizability."
)

RESEARCH = GoldAnnotation(
    url="https://example.org/r", title="Example research", article_type="RESEARCH",
    expected_labels=["KEY FINDING", "METHODOLOGY", "IMPLICATION", "CONCERN"],
    has_explicit_concern=True,
    key_facts=["medication confidence", "emergency department", "1275 adults"],
    expected_actionability="MONITOR",
)
NEWS = GoldAnnotation(
    url="https://example.org/n", title="Example news", article_type="NEWS",
    expected_labels=["KEY DEVELOPMENT", "TACTICAL WIN", "MARKET SIGNAL", "CONCERN"],
    has_explicit_concern=False, key_facts=["launch"], expected_actionability="CONTEXT ONLY",
)


def _ann(title, url, **kw):
    """Minimal annotation for loader tests, where only title/url matter."""
    return GoldAnnotation(
        url=url, title=title, article_type="NEWS", expected_labels=[],
        has_explicit_concern=False, key_facts=[], expected_actionability="MONITOR", **kw
    )


def _articles_dir(tmp_path, stamp, files):
    """Create runs/alert-<stamp>/articles/ containing {name: text}."""
    d = tmp_path / f"alert-{stamp}" / "articles"
    d.mkdir(parents=True)
    for name, text in files.items():
        (d / name).write_text(text)
    return d


def _summary(bullets, actionability="⚠️ MONITOR", article_type=None):
    s = {"summary": [{"type": "bullet", "text": b} for b in bullets], "actionability": actionability}
    if article_type:
        s["article_type"] = article_type
    return s


GOOD_RESEARCH = [
    "**KEY FINDING**: Medication confidence predicted emergency department visits (p<0.001).",
    "**METHODOLOGY**: Cross-sectional survey of 1,275 adults with cardiovascular risk factors.",
    "**IMPLICATION**: Improving confidence may reduce ED visits.",
    "**CONCERN**: Single health system sample limits generalizability.",
]


def test_accuracy_exact_label_set_required():
    ok = evaluate_accuracy(_summary(GOOD_RESEARCH), RESEARCH, ARTICLE)
    assert ok.labels_match_type
    # NEWS labels on a RESEARCH article no longer pass
    wrong = ["**KEY DEVELOPMENT**: x", "**TACTICAL WIN [🚀 SHIP NOW]**: y", "**MARKET SIGNAL [🟡 NOTABLE]**: z", "**CONCERN**: w"]
    assert not evaluate_accuracy(_summary(wrong), RESEARCH, ARTICLE).labels_match_type
    # a repeated label cannot stand in for a missing one
    dup = GOOD_RESEARCH[:1] * 2 + GOOD_RESEARCH[2:]
    assert not evaluate_accuracy(_summary(dup), RESEARCH, ARTICLE).labels_match_type


def test_accuracy_actionability_vocab_and_expected_category():
    m = evaluate_accuracy(_summary(GOOD_RESEARCH, "⚠️ MONITOR"), RESEARCH, ARTICLE)
    assert m.actionability_valid and m.actionability_correct
    m = evaluate_accuracy(_summary(GOOD_RESEARCH, "ℹ️ CONTEXT ONLY"), RESEARCH, ARTICLE)
    assert m.actionability_valid and not m.actionability_correct
    for bad in ("", "MONITOR", "⚠️ WHATEVER GOES", "two words"):
        assert not evaluate_accuracy(_summary(GOOD_RESEARCH, bad), RESEARCH, ARTICLE).actionability_valid


@pytest.mark.parametrize("tactical, market, expected", [
    ("[🚀 SHIP NOW]", "[🟡 NOTABLE]", True),
    ("[🚀/🗺️/👀]", "[🟡 NOTABLE]", False),      # placeholder left in
    ("", "[🟡 NOTABLE]", False),                  # no tag at all
    ("[🚀 SHIP NOW]", "[💥 BOOM]", False),        # emoji outside the allowed set
    ("[🚀🚀 SHIP NOW]", "[🟡 NOTABLE]", False),   # same tag twice
    ("[🚀][👀]", "[🟡 NOTABLE]", False),          # two bracket groups
])
def test_accuracy_tags_must_be_single_allowed_emoji(tactical, market, expected):
    bullets = ["**KEY DEVELOPMENT**: launch", f"**TACTICAL WIN {tactical}**: y",
               f"**MARKET SIGNAL {market}**: z", "**CONCERN**: No concerns stated in article."]
    assert evaluate_accuracy(_summary(bullets, "ℹ️ CONTEXT ONLY"), NEWS, ARTICLE).tag_selected is expected


def test_accuracy_untagged_label_sets_skip_the_tag_check():
    # RESEARCH bullets have no tagged labels: not subject to the check
    assert evaluate_accuracy(_summary(GOOD_RESEARCH), RESEARCH, ARTICLE).tag_selected


def test_accuracy_article_type_scored_only_when_reported():
    assert evaluate_accuracy(_summary(GOOD_RESEARCH), RESEARCH, ARTICLE).article_type_correct is None
    assert evaluate_accuracy(_summary(GOOD_RESEARCH, article_type="RESEARCH"), RESEARCH, ARTICLE).article_type_correct is True
    wrong = evaluate_accuracy(_summary(GOOD_RESEARCH, article_type="NEWS"), RESEARCH, ARTICLE)
    assert wrong.article_type_correct is False
    # key present but None = the classifier failed and the fallback prompt was used: counts as wrong
    failed = _summary(GOOD_RESEARCH); failed["article_type"] = None
    assert evaluate_accuracy(failed, RESEARCH, ARTICLE).article_type_correct is False
    assert wrong.accuracy_score < evaluate_accuracy(_summary(GOOD_RESEARCH, article_type="RESEARCH"), RESEARCH, ARTICLE).accuracy_score


def test_consistency_ignores_labels_when_comparing_bodies():
    a = _summary(["**KEY FINDING**: alpha beta gamma delta", "**CONCERN**: none"])
    b = _summary(["**KEY FINDING**: epsilon zeta eta theta", "**CONCERN**: none"])
    m = evaluate_consistency([a, b])
    assert m.structure_identical
    assert m.content_similarity < 0.2  # shared label words no longer inflate similarity


def test_hallucination_concern_checked_against_article():
    supported = detect_hallucinations(_summary(GOOD_RESEARCH), ARTICLE, RESEARCH)
    assert not supported.concern_is_fabricated
    invented = GOOD_RESEARCH[:3] + ["**CONCERN**: Regulators fined the manufacturer over undisclosed pricing kickbacks."]
    assert detect_hallucinations(_summary(invented), ARTICLE, RESEARCH).concern_is_fabricated
    # Article without an explicit concern: any real concern is fabricated, boilerplate is fine
    assert detect_hallucinations(_summary(["**CONCERN**: Sample bias worries."]), ARTICLE, NEWS).concern_is_fabricated
    assert not detect_hallucinations(_summary(["**CONCERN**: No concerns stated in article."]), ARTICLE, NEWS).concern_is_fabricated


def test_hallucination_comma_numbers_not_split():
    bullets = ["**KEY FINDING**: Enrolled 10,000 patients across 2,500 sites."]
    assert detect_hallucinations(_summary(bullets), "The trial enrolled 40 patients at 3 sites.", RESEARCH).invented_numbers
    assert not detect_hallucinations(_summary(["**KEY FINDING**: 1,275 adults surveyed."]), ARTICLE, RESEARCH).invented_numbers


def test_success_rate_uses_articles_times_runs():
    r = ModelResults(model="m", total_articles=2, runs_per_article=3, error_count=3)
    assert r.success_rate == pytest.approx(0.5)
    assert ModelResults(model="m", total_articles=1, runs_per_article=3, error_count=3).success_rate == 0.0


def test_load_articles_skips_titleless_annotation(tmp_path, monkeypatch):
    from Summarizer.evals import load_articles as la
    (tmp_path / "01-anything.content.md").write_text("Anything at all")
    monkeypatch.setattr(la, "GOLD_ANNOTATIONS", [_ann("", "u")])
    assert la.load_articles_from_directory(tmp_path) == []


def test_load_articles_walks_older_runs(tmp_path, monkeypatch):
    from Summarizer.evals import load_articles as la
    # Files are named NN-<slug(title)> by the pipeline; bodies need not contain the title
    _articles_dir(tmp_path, "20260102-000000", {"01-first-article-title.content.md": "body only"})
    _articles_dir(tmp_path, "20260101-000000", {"03-second-article-title.content.md": "DETROIT, MI - dateline first"})
    monkeypatch.setattr(la, "GOLD_ANNOTATIONS", [_ann("First article title", "u1"), _ann("Second article title", "u2")])
    arts = {a["url"]: a["content"] for a in la.load_articles_from_runs(tmp_path)}
    assert set(arts) == {"u1", "u2"}
    assert arts["u2"].startswith("DETROIT")


def test_load_articles_exact_slug_beats_prefix_and_ambiguity_is_skipped(tmp_path, monkeypatch):
    from Summarizer.evals import load_articles as la
    _articles_dir(tmp_path, "20260101-000000", {
        "01-target-article-title-extended-cut.content.md": "longer",
        "02-target-article-title.content.md": "exact",
    })
    monkeypatch.setattr(la, "GOLD_ANNOTATIONS", [_ann("Target Article Title", "exact"), _ann("Target Article", "ambiguous")])
    arts = {a["url"]: a["content"] for a in la.load_articles_from_runs(tmp_path)}
    assert arts == {"exact": "exact"}  # exact slug wins; the ambiguous prefix is skipped


def test_load_articles_prefers_newest_and_ignores_body_mentions(tmp_path, monkeypatch):
    from Summarizer.evals import load_articles as la
    _articles_dir(tmp_path, "20260102-000000", {
        "01-unrelated-piece.content.md": "This piece mentions Target Article Title in passing " * 50,
        "02-target-article-title.content.md": "new fetch",
    })
    _articles_dir(tmp_path, "20260101-000000", {"05-target-article-title.content.md": "old fetch"})
    monkeypatch.setattr(la, "GOLD_ANNOTATIONS", [_ann("Target Article Title", "t")])
    assert [a["content"] for a in la.load_articles_from_runs(tmp_path)] == ["new fetch"]


def test_evaluate_model_rejects_nonpositive_runs(monkeypatch):
    from Summarizer.evals import runner
    monkeypatch.setattr(runner.ModelEvaluator, "__init__", lambda self: None)
    with pytest.raises(ValueError):
        runner.ModelEvaluator().evaluate_model("m", [], runs=0)
