# Model Evaluation Framework

Comprehensive evaluation framework for testing LM Studio models on the Summarizer pipeline.

## Overview

This framework evaluates LLM models across three key dimensions:

1. **Accuracy** - Structural correctness and fact coverage
2. **Consistency** - Output stability across multiple runs
3. **Hallucination Detection** - Identification of fabricated content

## Quick Start

### Prerequisites

- LM Studio running with models loaded
- Python dependencies installed (see main README)
- Article content files in `runs/` directory

### Basic Usage

```bash
# Evaluate all available models
python3 -m Summarizer.cli eval

# Evaluate specific models
python3 -m Summarizer.cli eval --models "llama-chat-summary-3.2-3b,qwen3:latest"

# Run with more consistency tests
python3 -m Summarizer.cli eval --runs 5

# Specify custom output path
python3 -m Summarizer.cli eval --output my_eval_report.md
```

## Architecture

### Gold Standard (`gold_standard.py`)

Human-curated annotations for test articles:

- **Article Type**: RESEARCH, NEWS, OPINION, or PRESS_RELEASE
- **Expected Labels**: 4 bullet labels matching article type
- **Has Explicit Concern**: Whether article contains explicit limitations
- **Key Facts**: Important facts that should appear in summary
- **Expected Actionability**: Category like MONITOR, ACT NOW, etc.

Current test articles (see `GOLD_ANNOTATIONS`):
1. Patient-reported outcomes and medication confidence (RESEARCH)
2. AAOS Orthobiologics Registry (PRESS_RELEASE)
3. LogicMark medication reminder (PRESS_RELEASE)
4. ECU fear avoidance tool (NEWS)
5. SAT-151 testosterone replacement therapy and hematocrit (RESEARCH)
6. Beamion LUNG-1 patient-reported outcomes in HER2-mutated NSCLC (NEWS)
7. Lumbar bracing after short lumbar fusion (RESEARCH)

### Metrics (`metrics.py`)

Three dataclasses track different quality aspects:

#### AccuracyMetrics

Checks structural validity and content quality:

- `has_4_bullets` - Exactly 4 bullets present
- `labels_match_type` - Labels are exactly the annotation's `expected_labels` (order-insensitive, count-sensitive)
- `actionability_valid` - Actionability is `<emoji> <category>` with an allowed category (ACT NOW / MONITOR / RESEARCH NEEDED / CONTEXT ONLY)
- `actionability_correct` - Category matches the annotation's `expected_actionability`
- `tag_selected` - TACTICAL WIN / MARKET SIGNAL bullets carry exactly one allowed tag emoji, not a placeholder like `[🚀/🗺️/👀]`
- `facts_present` - Proportion of key facts from gold standard (0.0-1.0)
- `article_type_correct` - The classifier's type (recorded on the summary as `article_type`) matches the annotation; `None` for summaries without that field

**Scoring**: 50% structure (mean of the boolean checks above, `article_type_correct` included only when known) + 50% content (`facts_present`)

#### ConsistencyMetrics

Measures output stability across runs:

- `structure_identical` - Same bullet count and labels
- `content_similarity` - Jaccard similarity of bullet bodies (labels/tags excluded — `structure_identical` covers them)
- `actionability_stable` - Same actionability across runs

**Scoring**: Weighted average (40% structure + 40% similarity + 20% actionability)

#### HallucinationMetrics

Detects fabricated or incorrect content:

- `concern_is_fabricated` - A real CONCERN when the article states none, or one whose content words are mostly absent from the article
- `concern_is_benefit` - CONCERN describes positive outcome
- `concern_duplicates_other` - CONCERN duplicates another bullet
- `invented_numbers` - Numbers in summary not in article

**Scoring**: Proportion of flags that are True (lower is better)

### Runner (`runner.py`)

`ModelEvaluator` class orchestrates evaluation:

```python
from Summarizer.evals import ModelEvaluator

evaluator = ModelEvaluator()

# Get available models
models = evaluator.get_available_models()

# Load model
evaluator.load_model("llama-chat-summary-3.2-3b")

# Evaluate single model
results = evaluator.evaluate_model(
    model="llama-chat-summary-3.2-3b",
    articles=test_articles,
    runs=3
)

# Evaluate all models
all_results = evaluator.evaluate_all_models(
    articles=test_articles,
    runs=3
)
```

### Report (`report.py`)

Generates markdown reports with:

- Summary rankings table
- Best performers by metric
- Detailed per-model breakdown
- Interpretation guide

## Adding Test Articles

To add a new gold standard annotation:

1. Run the article through the pipeline to get content file
2. Manually review the article and identify:
   - Article type (RESEARCH/NEWS/OPINION/PRESS_RELEASE)
   - Expected bullet labels based on type
   - Whether explicit concerns are stated
   - Key facts that should appear
   - Expected actionability category
3. Add `GoldAnnotation` to `GOLD_ANNOTATIONS` in `gold_standard.py`

Example:

```python
GoldAnnotation(
    url="https://example.com/article",
    title="Article Title",
    article_type="RESEARCH",
    expected_labels=["KEY FINDING", "METHODOLOGY", "IMPLICATION", "CONCERN"],
    has_explicit_concern=True,  # Article mentions study limitations
    key_facts=[
        "sample size",
        "p-value",
        "confidence interval",
    ],
    expected_actionability="MONITOR",
    notes="Research paper with clear methodology section"
)
```

## Interpreting Results

### Accuracy Score Targets

- **>90%**: Excellent - Model consistently follows structure and captures facts
- **80-90%**: Good - Minor issues with tags or fact coverage
- **70-80%**: Fair - Structural issues or missing key facts
- **<70%**: Poor - Significant problems with format or content

### Consistency Score Targets

- **>85%**: Excellent - Highly stable across runs
- **70-85%**: Good - Minor variations in wording
- **50-70%**: Fair - Some structural instability
- **<50%**: Poor - Unpredictable output

### Hallucination Rate Targets

- **<10%**: Excellent - Minimal fabrication
- **10-20%**: Good - Occasional errors
- **20-40%**: Fair - Frequent hallucinations
- **>40%**: Poor - Unreliable summaries

## Common Issues

### Placeholder Tags

**Symptom**: Tag shows `[🚀/🗺️/👀]` instead of single emoji

**Cause**: Model failed to select specific tag, left placeholder from prompt

**Fix**: Check prompt clarity, try model with better instruction-following

### Fabricated Concerns

**Symptom**: CONCERN bullet contains text not in article

**Cause**: Model inventing limitations not stated by authors

**Fix**: Emphasize in prompt "ONLY if article EXPLICITLY states"

### Benefits as Concerns

**Symptom**: CONCERN describes positive outcome (e.g., "better adherence")

**Cause**: Model misclassifying benefits as concerns

**Fix**: Add examples of benefits vs concerns in prompt

### Empty Actionability

**Symptom**: Actionability field empty or malformed

**Cause**: Model skipping actionability generation

**Fix**: Check JSON schema enforcement, verify model supports structured output

## Development

### Running Tests

```bash
# Run all eval tests
python3 -m pytest Summarizer/tests/test_evals.py -v

# Test specific metric
python3 -m pytest Summarizer/tests/test_evals.py::test_accuracy_metrics -v
```

### Code Structure

```
Summarizer/evals/
├── __init__.py          # Package exports
├── README.md            # This file
├── gold_standard.py     # Test article annotations
├── metrics.py           # Evaluation metrics
├── runner.py            # Evaluation orchestration
└── report.py            # Report generation
```

### Adding New Metrics

1. Define metric dataclass in `metrics.py`
2. Implement evaluation function
3. Update `ModelResults` in `runner.py` to track metric
4. Update `generate_markdown_report()` in `report.py` to display metric

## Troubleshooting

### "No models available in LM Studio"

**Cause**: LM Studio not running or lms CLI not found

**Fix**:
- Start LM Studio
- Verify `lms` CLI installed: `~/.lmstudio/bin/lms ls`

### "No articles loaded for evaluation"

**Cause**: Can't find article content files

**Fix**:
- Specify `--articles-dir` pointing to runs/alert-*/articles/
- Ensure gold standard URLs match available articles

### "Failed to load model"

**Cause**: Model not downloaded or incorrect identifier

**Fix**:
- Check available models: `lms ls`
- Download model in LM Studio UI
- Verify model identifier matches exactly

## Future Enhancements

- [ ] Add ROUGE/BLEU scores for fact coverage
- [ ] Implement semantic similarity metrics (embeddings)
- [ ] Add cost/speed metrics (tokens/sec, latency)
- [ ] Support custom evaluation datasets
- [ ] Add A/B comparison mode
- [ ] Generate HTML reports with visualizations
