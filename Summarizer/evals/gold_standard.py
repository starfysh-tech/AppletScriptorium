"""Gold standard annotations for model evaluation.

Human-curated ground truth for evaluating summarizer quality across different
article types. Each annotation specifies expected bullet labels, key facts that
should appear, and whether explicit concerns are mentioned in the article.
"""

from dataclasses import dataclass
from typing import List, Literal

ArticleType = Literal["RESEARCH", "NEWS", "OPINION", "PRESS_RELEASE"]


@dataclass(frozen=True)
class GoldAnnotation:
    """Gold standard annotation for a single article."""

    url: str
    article_type: ArticleType
    expected_labels: List[str]  # Expected bullet labels based on article type
    has_explicit_concern: bool  # True if article contains explicit concerns/limitations
    key_facts: List[str]  # Key facts that should appear in summary (for recall check)
    expected_actionability: str  # Expected actionability category (e.g., "MONITOR", "ACT NOW")

    # Optional metadata for additional checks
    title: str = ""
    notes: str = ""  # Human notes about the article


# Gold standard annotations based on actual articles from runs
GOLD_ANNOTATIONS = [
    # RESEARCH - Patient-reported outcomes study
    GoldAnnotation(
        url="https://www.nature.com/articles/s41598-025-31255-z",
        title="Patient-reported outcomes and perceived medication confidence as predictors of healthcare utilization",
        article_type="RESEARCH",
        expected_labels=["KEY FINDING", "METHODOLOGY", "IMPLICATION", "CONCERN"],
        has_explicit_concern=True,  # Study mentions limitations in methodology
        key_facts=[
            "patient-reported outcomes",
            "medication confidence",
            "healthcare utilization",
            "emergency department",
            "hospital readmission",
        ],
        expected_actionability="MONITOR",
        notes="Research paper with methodology section, should identify study design and statistical approach"
    ),

    # PRESS RELEASE - AAOS Orthobiologics Registry
    GoldAnnotation(
        url="https://www.prnewswire.com/news-releases/aaos-establishes-orthobiologics-registry-to-advance-evidence-based-orthobiologics-research-302634205.html",
        title="AAOS Establishes Orthobiologics Registry",
        article_type="PRESS_RELEASE",
        expected_labels=["ANNOUNCEMENT", "STRATEGIC MOVE", "TIMELINE", "CONCERN"],
        has_explicit_concern=True,  # Mentions "robust real-world data...remains limited"
        key_facts=[
            "AAOS",
            "Orthobiologics Registry",
            "10 participating sites",
            "32.5 million Americans",
            "knee osteoarthritis",
            "platelet-rich plasma",
            "PRP",
        ],
        expected_actionability="MONITOR",
        notes="Press release with quotes, stats, company info. Concern: lack of existing evidence"
    ),

    # PRESS RELEASE - LogicMark medication reminder
    GoldAnnotation(
        url="https://www.eqs-news.com/news/corporate-news/logicmark-s-medication-reminder-tool-first-of-its-kind-in-the-medical-alert-industry/2241912",
        title="LogicMark's Medication Reminder Tool",
        article_type="PRESS_RELEASE",
        expected_labels=["ANNOUNCEMENT", "STRATEGIC MOVE", "TIMELINE", "CONCERN"],
        has_explicit_concern=False,  # No concerns stated in press release
        key_facts=[
            "LogicMark",
            "Freedom Alert Max",
            "medication reminders",
            "first time",
            "medical alert device",
            "Care Village app",
        ],
        expected_actionability="CONTEXT ONLY",
        notes="Product announcement with no concerns mentioned. Should output 'No concerns stated in article.'"
    ),

    # NEWS - ECU fear avoidance tool
    GoldAnnotation(
        url="https://www.news-medical.net/news/20251204/ECU-researchers-develop-new-tool-to-evaluate-fear-avoidance-behavior-after-concussion.aspx",
        title="ECU researchers develop new tool to evaluate fear avoidance behavior after concussion",
        article_type="NEWS",
        expected_labels=["KEY DEVELOPMENT", "TACTICAL WIN", "MARKET SIGNAL", "CONCERN"],
        has_explicit_concern=False,  # Article presents positive development, no concerns stated
        key_facts=[
            "Edith Cowan University",
            "ECU",
            "Fear Avoidance after Concussion Tool",
            "FACT",
            "28 items",
            "five minutes",
            "Liam Sherwood",
            "concussion",
        ],
        expected_actionability="MONITOR",
        notes="News article about research tool development. No concerns stated - tool is presented positively"
    ),

    # RESEARCH - Testosterone Replacement Therapy retrospective study
    GoldAnnotation(
        url="https://pmc.ncbi.nlm.nih.gov/articles/PMC12544051/",
        title="SAT-151 Real-World Effects of Testosterone Replacement Therapy on Hematocrit",
        article_type="RESEARCH",
        expected_labels=["KEY FINDING", "METHODOLOGY", "IMPLICATION", "CONCERN"],
        has_explicit_concern=True,  # Mentions need for prospective study of cardiovascular events
        key_facts=[
            "testosterone replacement therapy",
            "QADAM",
            "quality of life",
            "hematocrit",
            "6376",
            "cypionate",
            "retrospective",
        ],
        expected_actionability="MONITOR",
        notes="Retrospective cohort study showing TRT improves QADAM scores with rare high hematocrit"
    ),

    # NEWS - HER2-mutated NSCLC zongertinib trial
    GoldAnnotation(
        url="https://www.cancernursingtoday.com/post/beamion-lung-1-assessing-patient-reported-functioning-and-symptom-outcomes-in-pretreated-her2-mutated-nsclc",
        title="Assessing Patient-Reported Functioning and Symptom Outcomes in Pretreated HER2",
        article_type="NEWS",
        expected_labels=["KEY DEVELOPMENT", "TACTICAL WIN", "MARKET SIGNAL", "CONCERN"],
        has_explicit_concern=True,  # Study is ongoing, limited data
        key_facts=[
            "HER2",
            "NSCLC",
            "zongertinib",
            "Boehringer Ingelheim",
            "patient-reported",
            "physical functioning",
        ],
        expected_actionability="MONITOR",
        notes="News article about phase Ib trial for targeted treatment in HER2-mutated lung cancer"
    ),

    # RESEARCH - Lumbar bracing study
    GoldAnnotation(
        url="https://www.sciencedirect.com/science/article/pii/S187887502500926X",
        title="The Impact of Lumbar Bracing on Patient-Reported Outcomes In Short Lumbar Fusion",
        article_type="RESEARCH",
        expected_labels=["KEY FINDING", "METHODOLOGY", "IMPLICATION", "CONCERN"],
        has_explicit_concern=True,  # Questions efficacy of bracing
        key_facts=[
            "lumbar bracing",
            "lumbar fusion",
            "170 patients",
            "Oswestry Disability Index",
            "VAS",
            "MCS-12",
            "PLDF",
            "TLIF",
        ],
        expected_actionability="MONITOR",
        notes="Research showing bracing did not improve PROMs except isolated MCS-12 finding"
    ),
]


def get_annotation_by_url(url: str) -> GoldAnnotation | None:
    """Get gold standard annotation for a specific URL.

    Args:
        url: Article URL to look up

    Returns:
        GoldAnnotation if found, None otherwise
    """
    for annotation in GOLD_ANNOTATIONS:
        if annotation.url == url:
            return annotation
    return None


def get_annotations_by_type(article_type: ArticleType) -> List[GoldAnnotation]:
    """Get all gold standard annotations of a specific article type.

    Args:
        article_type: Article type to filter by

    Returns:
        List of matching GoldAnnotation objects
    """
    return [a for a in GOLD_ANNOTATIONS if a.article_type == article_type]
