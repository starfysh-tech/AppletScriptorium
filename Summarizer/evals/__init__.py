"""Model evaluation framework for Summarizer."""

from .metrics import AccuracyMetrics, ConsistencyMetrics, HallucinationMetrics
from .runner import ModelEvaluator
from .gold_standard import GOLD_ANNOTATIONS

__all__ = [
    "AccuracyMetrics",
    "ConsistencyMetrics",
    "HallucinationMetrics",
    "ModelEvaluator",
    "GOLD_ANNOTATIONS",
]
