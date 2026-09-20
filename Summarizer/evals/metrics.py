"""Evaluation metrics for model quality assessment.

This module implements three core metric classes:
1. AccuracyMetrics - Structural validity and fact coverage
2. ConsistencyMetrics - Output stability across runs
3. HallucinationMetrics - Detection of fabricated content
"""

from dataclasses import dataclass
import re
from typing import List


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for a single summary against gold standard."""

    has_4_bullets: bool  # True if exactly 4 bullets present
    labels_match_type: bool  # True if labels match article type (e.g., RESEARCH has KEY FINDING, METHODOLOGY, IMPLICATION, CONCERN)
    actionability_valid: bool  # True if actionability is properly formatted (emoji + label)
    facts_present: float  # Proportion of key facts from gold standard present in summary (0.0-1.0)
    article_type_correct: bool  # True if classified article type matches gold standard
    tag_selected: bool  # True if tags are selected (not placeholder [🚀/🗺️/👀])

    @property
    def accuracy_score(self) -> float:
        """Compute overall accuracy score (0.0-1.0).

        Weighted average of all metrics:
        - Structure (bullets, labels, actionability, tags): 50%
        - Content (facts_present): 50%
        Note: article_type_correct is excluded since we don't classify articles.
        """
        structure_score = (
            int(self.has_4_bullets) +
            int(self.labels_match_type) +
            int(self.actionability_valid) +
            int(self.tag_selected)
        ) / 4.0

        content_score = self.facts_present

        return 0.5 * structure_score + 0.5 * content_score


@dataclass
class ConsistencyMetrics:
    """Consistency metrics across multiple runs of the same article."""

    structure_identical: bool  # True if all runs have same bullet count and labels
    content_similarity: float  # Jaccard similarity of bullet content across runs (0.0-1.0)
    actionability_stable: bool  # True if actionability is the same across all runs

    @property
    def consistency_score(self) -> float:
        """Compute overall consistency score (0.0-1.0)."""
        return (
            int(self.structure_identical) * 0.4 +
            self.content_similarity * 0.4 +
            int(self.actionability_stable) * 0.2
        )


@dataclass
class HallucinationMetrics:
    """Hallucination detection metrics for a single summary."""

    concern_is_fabricated: bool  # True if CONCERN text does not appear in article
    concern_is_benefit: bool  # True if CONCERN describes a benefit (e.g., "better adherence")
    concern_duplicates_other: bool  # True if CONCERN duplicates another bullet's content
    invented_numbers: bool  # True if summary contains numbers not in article

    @property
    def hallucination_score(self) -> float:
        """Compute hallucination score (0.0-1.0, lower is better).

        Returns proportion of hallucination flags that are True.
        """
        flags = [
            self.concern_is_fabricated,
            self.concern_is_benefit,
            self.concern_duplicates_other,
            self.invented_numbers,
        ]
        return sum(flags) / len(flags)

    @property
    def has_hallucinations(self) -> bool:
        """True if any hallucination detected."""
        return any([
            self.concern_is_fabricated,
            self.concern_is_benefit,
            self.concern_duplicates_other,
            self.invented_numbers,
        ])


def evaluate_accuracy(summary: dict, gold: dict, article_content: str) -> AccuracyMetrics:
    """Evaluate summary accuracy against gold standard.

    Args:
        summary: Summary dict with "summary", "actionability", "model" fields
        gold: Gold standard annotation dict with "article_type", "expected_labels", "key_facts"
        article_content: Full article text for fact checking

    Returns:
        AccuracyMetrics object with all checks performed
    """
    from .gold_standard import GoldAnnotation

    # Reconstruct GoldAnnotation if needed
    if isinstance(gold, dict):
        gold_obj = GoldAnnotation(**gold)
    else:
        gold_obj = gold

    # Extract bullets from summary
    bullets = summary.get("summary", [])
    bullet_texts = [b.get("text", "") for b in bullets]
    bullet_labels = [b.get("text", "").split(":")[0].strip("*").strip() for b in bullets]

    # Check: exactly 4 bullets
    has_4_bullets = len(bullets) == 4

    # Normalize labels for comparison (remove tags like [TAG])
    normalized_labels = []
    for label in bullet_labels:
        # Remove tags in brackets and asterisks
        clean_label = re.sub(r'\s*\[.*?\]', '', label)
        clean_label = clean_label.strip('*').strip()
        normalized_labels.append(clean_label)

    # Check: labels are exactly the gold annotation's expected set for the
    # article type (RESEARCH -> KEY FINDING/METHODOLOGY/IMPLICATION/CONCERN,
    # etc.), order-insensitive but count-sensitive so a repeated label cannot
    # stand in for a missing one. Falls back to the NEWS label set when an
    # annotation carries no expected_labels.
    expected = gold.get("expected_labels") if isinstance(gold, dict) else getattr(gold, "expected_labels", None)
    if not expected:
        expected = ["KEY DEVELOPMENT", "TACTICAL WIN", "MARKET SIGNAL", "CONCERN"]
    labels_match = sorted(normalized_labels) == sorted(expected)

    # Check: actionability is valid (has emoji + label, not empty)
    actionability = summary.get("actionability", "")
    actionability_valid = bool(actionability) and len(actionability.split()) >= 2

    # Check: tags are selected (not placeholder)
    tag_selected = True
    bullets_text = "\n".join(bullet_texts)
    # Look for placeholder patterns like [🚀/🗺️/👀] or [🔴/🟡/⚫]
    placeholder_patterns = [
        r'\[🚀/🗺️/👀\]',
        r'\[🔴/🟡/⚫\]',
        r'\[TAG\]',
        r'\[action-tag\]',
        r'\[urgency-tag\]',
    ]
    for pattern in placeholder_patterns:
        if re.search(pattern, bullets_text):
            tag_selected = False
            break

    # Check: facts present (proportion of key facts found in summary)
    # Use fuzzy matching: fact is "found" if >50% of its words appear in summary
    summary_text = " ".join(bullet_texts).lower()
    summary_words = set(re.findall(r'\b\w+\b', summary_text))
    facts_found = 0
    for fact in gold_obj.key_facts:
        fact_words = set(re.findall(r'\b\w+\b', fact.lower()))
        if not fact_words:
            continue
        # Check word overlap
        overlap = len(fact_words & summary_words)
        # Single-word facts need exact match, multi-word facts need >50% overlap
        if len(fact_words) == 1:
            if overlap == 1:
                facts_found += 1
        elif overlap / len(fact_words) >= 0.5:
            facts_found += 1
    facts_present = facts_found / len(gold_obj.key_facts) if gold_obj.key_facts else 0.0

    # Check: article type correct (would need to track this from classification step)
    # For now, we'll mark as True since we don't have access to the classification result
    # This can be improved by passing the classification result to this function
    article_type_correct = True  # TODO: Pass actual classification result

    return AccuracyMetrics(
        has_4_bullets=has_4_bullets,
        labels_match_type=labels_match,
        actionability_valid=actionability_valid,
        facts_present=facts_present,
        article_type_correct=article_type_correct,
        tag_selected=tag_selected,
    )


def evaluate_consistency(summaries: List[dict]) -> ConsistencyMetrics:
    """Evaluate consistency across multiple runs of the same article.

    Args:
        summaries: List of summary dicts from multiple runs of the same article

    Returns:
        ConsistencyMetrics object with consistency checks
    """
    if len(summaries) < 2:
        # Can't evaluate consistency with fewer than 2 runs
        return ConsistencyMetrics(
            structure_identical=True,
            content_similarity=1.0,
            actionability_stable=True,
        )

    # Check: structure identical (same bullet count and labels)
    first_bullets = summaries[0].get("summary", [])
    first_labels = [b.get("text", "").split(":")[0].strip("*").strip() for b in first_bullets]

    structure_identical = True
    for summary in summaries[1:]:
        bullets = summary.get("summary", [])
        labels = [b.get("text", "").split(":")[0].strip("*").strip() for b in bullets]
        if len(bullets) != len(first_bullets) or labels != first_labels:
            structure_identical = False
            break

    # Check: content similarity (Jaccard similarity of bullet text)
    all_bullet_texts = []
    for summary in summaries:
        bullets = summary.get("summary", [])
        bullet_texts = [b.get("text", "").lower() for b in bullets]
        all_bullet_texts.append(set(" ".join(bullet_texts).split()))

    # Compute average pairwise Jaccard similarity
    similarity_scores = []
    for i in range(len(all_bullet_texts)):
        for j in range(i + 1, len(all_bullet_texts)):
            set_i = all_bullet_texts[i]
            set_j = all_bullet_texts[j]
            intersection = len(set_i & set_j)
            union = len(set_i | set_j)
            jaccard = intersection / union if union > 0 else 0.0
            similarity_scores.append(jaccard)

    content_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 1.0

    # Check: actionability stable
    first_actionability = summaries[0].get("actionability", "")
    actionability_stable = all(
        s.get("actionability", "") == first_actionability
        for s in summaries[1:]
    )

    return ConsistencyMetrics(
        structure_identical=structure_identical,
        content_similarity=content_similarity,
        actionability_stable=actionability_stable,
    )


def detect_hallucinations(summary: dict, article_content: str, gold: dict) -> HallucinationMetrics:
    """Detect hallucinated content in summary.

    Args:
        summary: Summary dict with "summary" field
        article_content: Full article text for fact checking
        gold: Gold standard annotation dict with "has_explicit_concern"

    Returns:
        HallucinationMetrics object with hallucination flags
    """
    from .gold_standard import GoldAnnotation

    # Reconstruct GoldAnnotation if needed
    if isinstance(gold, dict):
        gold_obj = GoldAnnotation(**gold)
    else:
        gold_obj = gold

    bullets = summary.get("summary", [])
    bullet_texts = [b.get("text", "") for b in bullets]

    # Find CONCERN bullet
    concern_bullet = None
    for bullet in bullets:
        text = bullet.get("text", "")
        if "**CONCERN" in text or "**CREDIBILITY" in text:
            concern_bullet = text
            break

    # Check 1: concern_is_fabricated
    concern_is_fabricated = False
    if concern_bullet and not gold_obj.has_explicit_concern:
        # Article has no explicit concerns, but model generated a CONCERN
        # Check if it's the standard "No concerns" text
        no_concern_phrases = [
            "no concerns stated in article",
            "no significant concerns identified",
            "no concerns identified",
            "no credibility concerns identified",
        ]
        is_no_concern = any(phrase in concern_bullet.lower() for phrase in no_concern_phrases)
        if not is_no_concern:
            concern_is_fabricated = True

    # Check 2: concern_is_benefit (concern describes ONLY positive outcome)
    # A false positive occurs when concern discusses lack of benefit or limited evidence
    # Only flag if concern is purely positive with no negative qualifiers
    concern_is_benefit = False
    if concern_bullet:
        benefit_words = ["better", "improve", "success", "effective", "positive", "higher",
                        "increased", "enhanced", "superior", "advantage", "benefit"]
        negative_qualifiers = ["not", "no", "lack", "limited", "without", "failed", "concern",
                               "risk", "need", "require", "further", "may", "might", "unclear"]
        concern_body = concern_bullet.split(":", 1)[1].lower() if ":" in concern_bullet else concern_bullet.lower()
        has_benefit = any(word in concern_body for word in benefit_words)
        has_negative = any(word in concern_body for word in negative_qualifiers)
        # Only flag if purely positive (benefit words present but no negative qualifiers)
        if has_benefit and not has_negative:
            concern_is_benefit = True

    # Check 3: concern_duplicates_other
    concern_duplicates_other = False
    if concern_bullet:
        # Extract concern text (after label)
        concern_text = concern_bullet.split(":", 1)[1].strip() if ":" in concern_bullet else concern_bullet
        concern_words = set(concern_text.lower().split())

        # Check other bullets for overlap
        for bullet in bullet_texts:
            if bullet == concern_bullet:
                continue
            bullet_text = bullet.split(":", 1)[1].strip() if ":" in bullet else bullet
            bullet_words = set(bullet_text.lower().split())

            # If >50% of concern words appear in another bullet, it's a duplicate
            if concern_words and bullet_words:
                overlap = len(concern_words & bullet_words)
                if overlap / len(concern_words) > 0.5:
                    concern_duplicates_other = True
                    break

    # Check 4: invented_numbers
    invented_numbers = False
    # Extract all numbers from summary
    summary_text = " ".join(bullet_texts)
    summary_numbers = set(re.findall(r'\b\d+\.?\d*\b', summary_text))

    # Extract all numbers from article (also strip commas for matching)
    article_text_normalized = article_content.replace(",", "")
    article_numbers = set(re.findall(r'\b\d+\.?\d*\b', article_text_normalized))

    # Check if any summary numbers are not in article
    # Filter out common numbers (1-100) as they're often generic or derived
    # Also filter out percentages which are often rounded
    summary_numbers_filtered = set()
    for n in summary_numbers:
        try:
            val = float(n)
            if val > 100:  # Only check large numbers
                summary_numbers_filtered.add(n)
        except ValueError:
            pass

    if summary_numbers_filtered:
        invented = summary_numbers_filtered - article_numbers
        if len(invented) > 1:  # Allow 1 number discrepancy (rounding, etc.)
            invented_numbers = True

    return HallucinationMetrics(
        concern_is_fabricated=concern_is_fabricated,
        concern_is_benefit=concern_is_benefit,
        concern_duplicates_other=concern_duplicates_other,
        invented_numbers=invented_numbers,
    )
