---
name: evaluation-engineering
description: Define reproducible quality, safety, cost, extraction, deduplication, and agent metrics.
---

# Evaluation Engineering

1. Version fixtures, datasets, schemas, thresholds, prompts, provider/model, extractor, and seed where relevant.
2. Separate unit, integration, offline, and live-safety evidence.
3. Measure extraction precision/recall/completeness, duplicate precision/recall, qualification calibration, provenance, and policy compliance.
4. Measure agent success, tool validity, grounding, terminal outcomes, steps, latency, tokens, cost, and fallback.
5. Measure authorization/privacy/source-abuse refusal and browser recovery.
6. Require a baseline and confidence interval or fixed repeat count.
7. Never lower thresholds to achieve a passing CI result; report uncertainty and unresolved samples.
