# W1-25 — Product-matching baseline and embedding feasibility

**Status:** Initial synthetic-fixture implementation and evaluation; real retailer validation pending.

## Goal

Determine whether validated product identifiers plus normalized brand/model/variant comparisons are sufficiently reliable for the ShopAgent MVP before introducing BGE-M3 or a reranker.

## Scope and provisional identity policy

- **Exact purchasable listing identity**: same brand, model, relevant product variant and condition. Compare prices *only after* grouping equivalent offers.
- Same parent product but different memory, storage, color, connector, edition or condition is conservatively a **non-match** for automatic price grouping.
- Empty or contradictory identifiers/attributes may require **uncertain / review**, rather than a forced match.
- **Team decision outstanding:** Whether to group color variants and refurbished condition as the same canonical product with separate offers. This may change label policy.

## Data

`evaluation/product_pairs.jsonl` contains **92 synthetic labeled pairs** derived from **48 synthetic base listings** in `evaluation/product_matching/mock_products.json`, plus eight intentionally difficult pair-only stress variations. No live API responses or real retailer identifiers were used.

- Development: 60 pairs from 8 product families.
- Holdout: 32 pairs from 4 different product families.
- The holdout contains 14 positive matches and 18 non-matches.
- All example GTINs and MPNs are invented. Synthetic GTINs pass checksum format validation; a valid checksum is **not** proof that a GTIN has been assigned to a real item.
- Product families are split so repeated titles of the same model cannot leak between development and holdout.

## Baseline method

1. Normalize brands/models/MPNs and variant attribute values by case-folding and stripping spacing/punctuation.
2. Validate GTIN-8/12/13/14 checksums and compare valid GTINs in padded GTIN-14 form.
3. Reject obvious brand, model or known-variant conflicts (`non_match`).
4. Conflicting valid GTINs or conflicting brand-scoped MPNs yield `uncertain` unless a stronger mismatch is already known.
5. Accept consistent matching GTINs; otherwise accept consistent brand + MPN.
6. As a fallback with missing IDs, require matching normalized brand/model, complete symmetric variant coverage and at least one distinguishing attribute beyond condition.
7. Ignore `price_usd` and retailer names as product identity signals.

The input is a provisional ProductOffer-like dictionary, **not** a finalized backend schema. When W1-12 is finalized, a thin input adapter should translate from `backend/app/schemas/product.py` into this matcher.

## Local synthetic evaluation

Commands:

```bash
python evaluation/product_matching/validate_dataset.py
python -m unittest discover -s evaluation/product_matching -p 'test_*.py' -v
python evaluation/product_matching/evaluate.py --split holdout --output evaluation/product_matching/results_holdout.json
```

**Holdout:** 32 pairs, TP=12, FP=2, FN=2, TN=16. Precision **0.8571**, recall **0.8571**, F1 **0.8571**. One pair produced `uncertain` (automatic-decision coverage **0.9688**). `uncertain` is treated as not matched for binary metrics, and is separately counted. See `results_holdout.json` for examples.

**Do not present this as an estimated real-world accuracy.** The examples are synthetic and biased towards fields expected by the algorithm. Metrics here primarily show behavior, demonstrate the evaluation harness and identify known failure modes.


### Updated Development Evaluation

Following the initial evaluation, three safeguards were introduced:

1. Accessory detection to prevent accessories from being
   incorrectly grouped with their parent products.
2. RAM consistency validation between product titles
   and structured attributes.
3. Storage consistency validation to detect stale or
   contradictory product specifications.

The updated baseline was evaluated on 60 synthetic
development pairs.

| Metric | Result |
|---|---|
| Precision | 100.00% |
| Recall | 92.31% |
| F1-score | 96.00% |
| True positives | 24 |
| False positives | 0 |
| False negatives | 2 |
| True negatives | 34 |
| Automatic-decision coverage | 95.00% |

All 14 automated unit tests passed.

Three pairs received an uncertain decision:
- Missing color information
- Conflicting valid GTINs
- Contradictory title and structured storage attributes

The updated storage safeguard prevented the previously
observed false-positive match involving inconsistent
storage specifications.

These results reflect synthetic development data only.
They are not estimates of real-world matching performance.

The original holdout examples were inspected during
development, so that split can no longer be considered
fully independent for evaluating the revised matcher.
A new independently labeled retailer sample is required
before making production-level accuracy claims.

## Example errors and non-match safeguards

| Holdout example | Gold label | Baseline | Lesson |
|---|---|---|---|
| `stress_holdout_accessory` | non-match | match | If normalization wrongly labels an accessory as its parent product, trusted structured attributes can cause false positives. Need accessory/bundle checks. |
| `stress_holdout_missing_model` | match | uncertain | Sparse API responses can reduce recall; consider safe additional evidence. |
| `stress_holdout_model_alias` | match | non-match | Simple exact normalized model strings miss valid aliases; consider a maintained alias table or text/embedding candidate retrieval. |
| `stress_holdout_stale_ram` | non-match | match | Stale or incorrect structured memory attributes can produce incorrect merges. Cross-check title-extracted variant tokens. |

Existing safeguards block explicit model/version, storage, condition, color, edition and connector disagreements; conflicting high-confidence product identifiers trigger review.

## BGE-M3 and reranker feasibility

The [BAAI BGE-M3 model card](https://huggingface.co/BAAI/bge-m3) describes a multilingual embedding model supporting dense, sparse and multi-vector retrieval. The [BGE project documentation](https://bge-model.com/bge/bge_m3) lists a large model footprint (about 569M parameters and 2.27GB model size), which adds deployment and evaluation complexity. The model is **not installed or benchmarked in this starter**.

**Possible value:** Improve candidate discovery when model aliases or noisy retailer descriptions prevent exact matching. A reranker may improve ranking of candidate matches after retrieval.

**Critical risk:** Semantic similarity is not the same as SKU/variant identity. Embeddings can rank the 128GB and 256GB versions very close; a rule-based variant-conflict gate should remain authoritative regardless of similarity score.

**Recommendation for P0:** Start with exact IDs + conservative normalized attributes, error logging and an explicit `uncertain` outcome. Do **not** add BGE-M3 as a P0 dependency on the basis of synthetic data alone. Revisit embeddings after labeling representative retailer offers and measuring failure modes, precision/recall impact, latency and memory. If aliases dominate false negatives, first test a small alias dictionary; then benchmark an embedding + reranking approach with the same untouched holdout protocol.

## Next steps to complete W1-25 with realistic evidence

1. Confirm match policy for color, condition and bundles with PM/Data Science.
2. Obtain the canonical ProductOffer schema from W1-12 and representative source payloads/mock adapter fixtures.
3. Independently label a realistic sample of same-product, different-variant and accessory pairs. Keep it separate from synthetic examples.
4. Run the unchanged baseline against that new holdout and inspect false-positive merges before deciding on embeddings.
5. Add a small integration adapter only after coordinating with backend owners; no API keys or live scraper access are required for this evaluation.

## Deliverable locations

- Dataset: `evaluation/product_pairs.jsonl`
- Baseline code/tests/fixtures/results: `evaluation/product_matching/`
- This report: `docs/matching-baseline.md`
