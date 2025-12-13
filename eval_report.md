# Model Evaluation Report

Evaluated 11 models across 2 articles.

## Summary Rankings

| Rank | Model | Accuracy | Consistency | Hallucination Rate | Success Rate |
|------|-------|----------|-------------|-------------------|--------------|
| 1 | `kurtis-e1-smollm2-1.7b-instruct-mlx` | 73.75% | 15.08% | 50.00% | -100.00% |
| 2 | `allenai/olmocr-2-7b` | 68.75% | 91.20% | 0.00% | 100.00% |
| 3 | `gemma-3-4b-it` | 68.75% | 85.52% | 0.00% | 100.00% |
| 4 | `ibm/granite-4-h-tiny` | 68.75% | 77.63% | 0.00% | 100.00% |
| 5 | `google/gemma-3n-e4b` | 67.50% | 97.95% | 0.00% | 100.00% |
| 6 | `mistral-7b-instruct-v0.3-mixed-6-8-bit` | 66.25% | 24.55% | 0.00% | 100.00% |
| 7 | `mistral-7b-instruct-finetuned-cui` | 62.50% | 95.08% | 100.00% | 100.00% |
| 8 | `llama-3.2-3b-instruct-mlx` | 50.00% | 41.61% | 0.00% | 100.00% |
| 9 | `phi-3-mini-4k-instruct` | 0.00% | 0.00% | 0.00% | -900.00% |
| 10 | `qwen/qwen3-vl-4b` | 0.00% | 0.00% | 0.00% | 0.00% |
| 11 | `smollm2-1.7b-instruct-mlx-393a7` | 0.00% | 0.00% | 0.00% | 0.00% |

## Detailed Results

### Best Performers

- **Best Accuracy**: `kurtis-e1-smollm2-1.7b-instruct-mlx` (73.75%)
- **Best Consistency**: `google/gemma-3n-e4b` (97.95%)
- **Lowest Hallucination Rate**: `allenai/olmocr-2-7b` (0.00%)
- **Best Success Rate**: `allenai/olmocr-2-7b` (100.00%)

### Model: `kurtis-e1-smollm2-1.7b-instruct-mlx`

**Overall Metrics:**

- Accuracy Score: 73.75%
- Consistency Score: 15.08%
- Hallucination Rate: 50.00%
- Success Rate: -100.00%
- Errors: 4/2

**Accuracy Breakdown:**

- Has 4 bullets: 2/2 (100.0%)
- Labels match type: 2/2 (100.0%)
- Actionability valid: 2/2 (100.0%)
- Tag selected (not placeholder): 2/2 (100.0%)
- Average fact coverage: 47.5%

**Hallucination Breakdown:**

- Fabricated concerns: 0/2 (0.0%)
- Concern is benefit: 0/2 (0.0%)
- Concern duplicates other bullet: 1/2 (50.0%)
- Invented numbers: 0/2 (0.0%)

**Consistency Breakdown:**

- Structure identical: 0/2 (0.0%)
- Actionability stable: 0/2 (0.0%)
- Average content similarity: 37.7%

---

### Model: `allenai/olmocr-2-7b`

**Overall Metrics:**

- Accuracy Score: 68.75%
- Consistency Score: 91.20%
- Hallucination Rate: 0.00%
- Success Rate: 100.00%
- Errors: 0/2

**Accuracy Breakdown:**

- Has 4 bullets: 2/2 (100.0%)
- Labels match type: 2/2 (100.0%)
- Actionability valid: 2/2 (100.0%)
- Tag selected (not placeholder): 2/2 (100.0%)
- Average fact coverage: 37.5%

**Hallucination Breakdown:**

- Fabricated concerns: 0/2 (0.0%)
- Concern is benefit: 0/2 (0.0%)
- Concern duplicates other bullet: 0/2 (0.0%)
- Invented numbers: 0/2 (0.0%)

**Consistency Breakdown:**

- Structure identical: 2/2 (100.0%)
- Actionability stable: 2/2 (100.0%)
- Average content similarity: 78.0%

---

### Model: `gemma-3-4b-it`

**Overall Metrics:**

- Accuracy Score: 68.75%
- Consistency Score: 85.52%
- Hallucination Rate: 0.00%
- Success Rate: 100.00%
- Errors: 0/2

**Accuracy Breakdown:**

- Has 4 bullets: 2/2 (100.0%)
- Labels match type: 2/2 (100.0%)
- Actionability valid: 2/2 (100.0%)
- Tag selected (not placeholder): 2/2 (100.0%)
- Average fact coverage: 37.5%

**Hallucination Breakdown:**

- Fabricated concerns: 0/2 (0.0%)
- Concern is benefit: 0/2 (0.0%)
- Concern duplicates other bullet: 0/2 (0.0%)
- Invented numbers: 0/2 (0.0%)

**Consistency Breakdown:**

- Structure identical: 2/2 (100.0%)
- Actionability stable: 2/2 (100.0%)
- Average content similarity: 63.8%

---

### Model: `ibm/granite-4-h-tiny`

**Overall Metrics:**

- Accuracy Score: 68.75%
- Consistency Score: 77.63%
- Hallucination Rate: 0.00%
- Success Rate: 100.00%
- Errors: 0/2

**Accuracy Breakdown:**

- Has 4 bullets: 2/2 (100.0%)
- Labels match type: 2/2 (100.0%)
- Actionability valid: 2/2 (100.0%)
- Tag selected (not placeholder): 2/2 (100.0%)
- Average fact coverage: 37.5%

**Hallucination Breakdown:**

- Fabricated concerns: 0/2 (0.0%)
- Concern is benefit: 0/2 (0.0%)
- Concern duplicates other bullet: 0/2 (0.0%)
- Invented numbers: 0/2 (0.0%)

**Consistency Breakdown:**

- Structure identical: 1/2 (50.0%)
- Actionability stable: 2/2 (100.0%)
- Average content similarity: 94.1%

---

### Model: `google/gemma-3n-e4b`

**Overall Metrics:**

- Accuracy Score: 67.50%
- Consistency Score: 97.95%
- Hallucination Rate: 0.00%
- Success Rate: 100.00%
- Errors: 0/2

**Accuracy Breakdown:**

- Has 4 bullets: 2/2 (100.0%)
- Labels match type: 2/2 (100.0%)
- Actionability valid: 2/2 (100.0%)
- Tag selected (not placeholder): 1/2 (50.0%)
- Average fact coverage: 47.5%

**Hallucination Breakdown:**

- Fabricated concerns: 0/2 (0.0%)
- Concern is benefit: 0/2 (0.0%)
- Concern duplicates other bullet: 0/2 (0.0%)
- Invented numbers: 0/2 (0.0%)

**Consistency Breakdown:**

- Structure identical: 2/2 (100.0%)
- Actionability stable: 2/2 (100.0%)
- Average content similarity: 94.9%

---

### Model: `mistral-7b-instruct-v0.3-mixed-6-8-bit`

**Overall Metrics:**

- Accuracy Score: 66.25%
- Consistency Score: 24.55%
- Hallucination Rate: 0.00%
- Success Rate: 100.00%
- Errors: 0/2

**Accuracy Breakdown:**

- Has 4 bullets: 2/2 (100.0%)
- Labels match type: 2/2 (100.0%)
- Actionability valid: 2/2 (100.0%)
- Tag selected (not placeholder): 2/2 (100.0%)
- Average fact coverage: 32.5%

**Hallucination Breakdown:**

- Fabricated concerns: 0/2 (0.0%)
- Concern is benefit: 0/2 (0.0%)
- Concern duplicates other bullet: 0/2 (0.0%)
- Invented numbers: 0/2 (0.0%)

**Consistency Breakdown:**

- Structure identical: 0/2 (0.0%)
- Actionability stable: 0/2 (0.0%)
- Average content similarity: 61.4%

---

### Model: `mistral-7b-instruct-finetuned-cui`

**Overall Metrics:**

- Accuracy Score: 62.50%
- Consistency Score: 95.08%
- Hallucination Rate: 100.00%
- Success Rate: 100.00%
- Errors: 0/2

**Accuracy Breakdown:**

- Has 4 bullets: 2/2 (100.0%)
- Labels match type: 2/2 (100.0%)
- Actionability valid: 2/2 (100.0%)
- Tag selected (not placeholder): 2/2 (100.0%)
- Average fact coverage: 25.0%

**Hallucination Breakdown:**

- Fabricated concerns: 0/2 (0.0%)
- Concern is benefit: 0/2 (0.0%)
- Concern duplicates other bullet: 2/2 (100.0%)
- Invented numbers: 0/2 (0.0%)

**Consistency Breakdown:**

- Structure identical: 2/2 (100.0%)
- Actionability stable: 2/2 (100.0%)
- Average content similarity: 87.7%

---

### Model: `llama-3.2-3b-instruct-mlx`

**Overall Metrics:**

- Accuracy Score: 50.00%
- Consistency Score: 41.61%
- Hallucination Rate: 0.00%
- Success Rate: 100.00%
- Errors: 0/2

**Accuracy Breakdown:**

- Has 4 bullets: 2/2 (100.0%)
- Labels match type: 2/2 (100.0%)
- Actionability valid: 0/2 (0.0%)
- Tag selected (not placeholder): 2/2 (100.0%)
- Average fact coverage: 25.0%

**Hallucination Breakdown:**

- Fabricated concerns: 0/2 (0.0%)
- Concern is benefit: 0/2 (0.0%)
- Concern duplicates other bullet: 0/2 (0.0%)
- Invented numbers: 0/2 (0.0%)

**Consistency Breakdown:**

- Structure identical: 0/2 (0.0%)
- Actionability stable: 1/2 (50.0%)
- Average content similarity: 79.0%

---

### Model: `phi-3-mini-4k-instruct`

**Overall Metrics:**

- Accuracy Score: 0.00%
- Consistency Score: 0.00%
- Hallucination Rate: 0.00%
- Success Rate: -900.00%
- Errors: 20/2

---

### Model: `qwen/qwen3-vl-4b`

**Overall Metrics:**

- Accuracy Score: 0.00%
- Consistency Score: 0.00%
- Hallucination Rate: 0.00%
- Success Rate: 0.00%
- Errors: 2/2

---

### Model: `smollm2-1.7b-instruct-mlx-393a7`

**Overall Metrics:**

- Accuracy Score: 0.00%
- Consistency Score: 0.00%
- Hallucination Rate: 0.00%
- Success Rate: 0.00%
- Errors: 2/2

---

## Interpretation Guide

### Metrics Explained

**Accuracy Score** (higher is better):
- Measures structural correctness and fact coverage
- Weighted: 50% structure (bullets, labels, tags, actionability) + 50% content (facts)

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
