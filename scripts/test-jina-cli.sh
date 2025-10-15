#!/bin/bash
# CLI commands to validate Jina AI behavior

JINA_KEY="jina_b9b85c66b63641cb974c3c536eca329bc13ojUPAu2R-_c6PIwITUqFW6EXu"

echo "=== Test 1: Wiley (best quality) ==="
curl -H "Authorization: Bearer $JINA_KEY" \
  "https://r.jina.ai/https://obgyn.onlinelibrary.wiley.com/doi/10.1111/1471-0528.18355" \
  | head -100

echo -e "\n\n=== Test 2: ScienceDirect ==="
curl -H "Authorization: Bearer $JINA_KEY" \
  "https://r.jina.ai/https://www.sciencedirect.com/science/article/abs/pii/S0883540325012227" \
  | head -100

echo -e "\n\n=== Test 3: PMC/NIH ==="
curl -H "Authorization: Bearer $JINA_KEY" \
  "https://r.jina.ai/https://pmc.ncbi.nlm.nih.gov/articles/PMC12475716/" \
  | head -100

echo -e "\n\n=== Test 4: UroToday (poor quality) ==="
curl -H "Authorization: Bearer $JINA_KEY" \
  "https://r.jina.ai/https://www.urotoday.com/recent-abstracts/pelvic-health-reconstruction/pelvic-prolapse/163406-patient-reported-outcome-measures-used-to-assess-surgical-interventions-for-pelvic-organ-prolapse-stress-urinary-incontinence-and-mesh-complications-a-scoping-review-for-the-development-of-the-appraise-prom.html" \
  | head -100

echo -e "\n\n=== Test 5: News10 (Cloudflare challenge) ==="
curl -H "Authorization: Bearer $JINA_KEY" \
  "https://r.jina.ai/https://www.news10.com/news/local-news/" \
  | head -100
