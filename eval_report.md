# Model Evaluation Report

Evaluated 1 models across 2 articles.

## Summary Rankings

| Rank | Model | Accuracy | Consistency | Hallucination Rate | Success Rate |
|------|-------|----------|-------------|-------------------|--------------|
| 1 | `mistral-7b-instruct-v0.3-mixed-6-8-bit` | 61.25% | 59.29% | 0.00% | 100.00% |

## Detailed Results

### Best Performers

- **Best Accuracy**: `mistral-7b-instruct-v0.3-mixed-6-8-bit` (61.25%)
- **Best Consistency**: `mistral-7b-instruct-v0.3-mixed-6-8-bit` (59.29%)
- **Lowest Hallucination Rate**: `mistral-7b-instruct-v0.3-mixed-6-8-bit` (0.00%)
- **Best Success Rate**: `mistral-7b-instruct-v0.3-mixed-6-8-bit` (100.00%)

### Model: `mistral-7b-instruct-v0.3-mixed-6-8-bit`

**Overall Metrics:**

- Accuracy Score: 61.25%
- Consistency Score: 59.29%
- Hallucination Rate: 0.00%
- Success Rate: 100.00%
- Errors: 0/2

**Accuracy Breakdown:**

- Has 4 bullets: 2/2 (100.0%)
- Labels match type: 2/2 (100.0%)
- Actionability valid: 2/2 (100.0%)
- Tag selected (not placeholder): 2/2 (100.0%)
- Average fact coverage: 22.5%

**Hallucination Breakdown:**

- Fabricated concerns: 0/2 (0.0%)
- Concern is benefit: 0/2 (0.0%)
- Concern duplicates other bullet: 0/2 (0.0%)
- Invented numbers: 0/2 (0.0%)

**Consistency Breakdown:**

- Structure identical: 1/2 (50.0%)
- Actionability stable: 2/2 (100.0%)
- Average content similarity: 48.2%

---

## Interpretation Guide

### Metrics Explained

**Accuracy Score** (higher is better):
- Measures structural correctness and fact coverage
- Weighted: 60% structure (bullets, labels, tags, actionability) + 40% content (facts, type)

**Consistency Score** (higher is better):
- Measures output stability across multiple runs
- Models with high consistency produce similar outputs for the same input

**Hallucination Rate** (lower is better):
- Proportion of summaries with fabricated content
- Checks for invented concerns, misclassified benefits, duplicates, and invented numbers

**Success Rate** (higher is better):
- Proportion of articles successfully summarized without errors
- Models with low success rates may timeout or fail frequently

### Common Issues to Look For

1. **Placeholder tags** (`[🚀/🗺️/👀]`): Model failed to select specific tag
2. **Fabricated concerns**: Model invented concerns not in article
3. **Benefits as concerns**: Model misclassified positive outcomes as concerns
4. **Empty actionability**: Model failed to generate actionability indicator
5. **Low fact coverage**: Summary missing key information from article
