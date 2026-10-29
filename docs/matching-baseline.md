
# W1-25 — Product-Matching Baseline and Embedding Feasibility

**Status:** Initial synthetic-fixture baseline implemented and tested. Original holdout retained for diagnostic use only; independent real-retailer validation pending.

## Goal

Determine whether validated product identifiers and normalized brand, model, and variant comparisons are sufficiently reliable for the ShopAgent/PriceLumi MVP before introducing BGE-M3 embeddings or a reranker.

## Scope and Provisional Identity Policy

- **Exact purchasable-offer equivalence:** Group offers only when their brand, model, relevant product variant, and condition are compatible. Compare prices **after** determining that the offers are equivalent.
- **Different variants are not interchangeable:** Explicit disagreements in memory, storage, color, connector, edition, or condition result in `non_match` for automatic price grouping.
- **Missing information requires caution:** If an identifying variant field is present on one side but missing on the other, return `uncertain`, including when GTINs or brand-scoped MPNs match.
- **Contradictory identifiers require review:** Conflicting valid GTINs or brand-scoped MPNs yield `uncertain` unless a stronger incompatibility has already been established.
- **Accessories and bundles are distinct cases:** An accessory should not be grouped with its primary product. Bundles or multipacks with unverified contents are treated conservatively rather than assumed equivalent to a standalone item or another bundle.
- **`uncertain` is a deliberate outcome:** The matcher does not force every pair into a match or non-match classification.

**Outstanding team decision:** Whether color variants and refurbished/used condition should share a canonical parent product while remaining separate purchasable offers. This could alter the final labeling and grouping policy.

**Current limitation:** If both offers omit the same important attribute, a matching identifier may still be sufficient for `match`. Category-specific completeness requirements must be agreed when the canonical `ProductOffer` schema is finalized.

## Data

`evaluation/product_pairs.jsonl` contains **92 synthetic labeled product pairs**, derived from **48 synthetic base listings** in `evaluation/product_matching/mock_products.json` and additional pair-level stress variations. No live retailer API responses or real retailer identifiers were used.

| Dataset split | Pairs | Positive labels | Negative labels | Product families | Current role |
|---|---:|---:|---:|---:|---|
| Development | 60 | 26 | 34 | 8 | Development and regression analysis |
| Original holdout | 32 | 14 | 18 | 4 | **Diagnostic fixtures only** |
| **Total** | **92** | **40** | **52** | **12** | Synthetic evaluation suite |

The original family-based split avoided overlap between development and original holdout families. However, **the original holdout examples were subsequently inspected during matcher development**, so that split is no longer independent for the revised implementation.

All example GTINs and MPNs are invented. A valid GTIN checksum establishes only checksum validity; it does **not** prove that the number has been assigned to a real product.

## Baseline Method

The matcher is implemented in `evaluation/product_matching/baseline.py` and returns one of `match`, `non_match`, or `uncertain`, alongside a reason and evidence category.

1. Normalize brands, models, MPNs, and structured variant values using case-folding and punctuation/whitespace removal.
2. Validate GTIN-8/12/13/14 checksums and compare valid identifiers in zero-padded GTIN-14 form.
3. Check product-title information against structured RAM and storage values; return `uncertain` for detected contradictions.
4. Distinguish accessories, standalone products, and bundles/multipacks using conservative title-based signals. Prevent accessory-to-product matches, and abstain when bundle contents cannot be verified.
5. Reject explicit brand, model, and shared-variant conflicts as `non_match`.
6. Return `uncertain` for conflicting valid GTINs or conflicting brand-scoped MPNs.
7. **Before accepting a GTIN or MPN match**, check that both offers provide the same set of variant fields; if a field is missing on one side, return `uncertain`.
8. Accept consistent matching GTINs, or consistent brand-scoped MPNs, when no earlier conflict or incompleteness rule applies.
9. When identifiers are insufficient, require consistent normalized brand/model, symmetric variant coverage, and at least one identifying variant beyond condition.
10. Do not use retailer name or price as product identity evidence.

The input is a provisional `ProductOffer`-like dictionary, **not** the finalized backend schema. After W1-12 is finalized, an adapter should map canonical `ProductOffer` records into the matcher without silently inventing missing attributes.

## Local Validation and Testing

Run the following commands from the repository root:

```bash
python3 evaluation/product_matching/validate_dataset.py
python3 -m unittest discover -s evaluation/product_matching -p "test_*.py" -v
python3 evaluation/product_matching/evaluate.py --split development
python3 evaluation/product_matching/evaluate.py --split holdout
```

**Verified local results (latest review changes):**

- Dataset validator passed: 48 base listings and 92 labeled pairs.
- **27/27 unit tests passed**: 14 original tests, 5 missing-variant policy tests, and 8 accessory/bundle tests.
- Development metrics remained unchanged after the review fixes.

### Synthetic Development Evaluation

The following results are from **60 synthetic development pairs**:

| Metric | Result |
|---|---:|
| True positives (TP) | 24 |
| False positives (FP) | 0 |
| False negatives (FN) | 2 |
| True negatives (TN) | 34 |
| Precision | **100.00%** |
| Recall | **92.31%** |
| F1-score | **96.00%** |
| Automatic-decision coverage | **95.00%** |
| Decisions: `match` / `non_match` / `uncertain` | 24 / 33 / 3 |

Three pairs received `uncertain` decisions:

- `stress_dev_missing_color`: one listing lacks a variant attribute.
- `stress_dev_conflicting_gtin`: two valid GTINs conflict.
- `stress_dev_stale_parsed_storage`: title storage contradicts a structured storage value.

For binary scoring, `uncertain` is treated as **not matched**, while abstentions are separately counted in decision coverage. Thus, an abstention on a truly matching pair contributes to false negatives under this evaluation protocol.

**These figures describe synthetic development fixtures only. They are not real-retailer accuracy estimates.**

### Original Holdout — Diagnostic Evaluation Only

The original synthetic holdout consists of **32 labeled pairs across four product families**. Although it was initially reserved for evaluation, examples from this split were examined and used to guide subsequent matcher changes. Consequently, the set is **not an independent holdout for the current matcher**. The results below are retained only for regression diagnosis and error analysis.

**Latest local evaluation of the current matcher:**

| Metric | Result |
|---|---:|
| Evaluated pairs | 32 |
| True positives (TP) | 12 |
| False positives (FP) | 1 |
| False negatives (FN) | 2 |
| True negatives (TN) | 17 |
| Precision | **92.31%** |
| Recall | **85.71%** |
| F1-score | **88.89%** |
| Automatic-decision coverage | **96.88%** |
| Decisions: `match` / `non_match` / `uncertain` | 13 / 18 / 1 |

**Current diagnostic cases:**

| Pair ID | True label | Current decision | Interpretation |
|---|---|---|---|
| `stress_holdout_missing_model` | Match | `uncertain` | Sparse identity fields reduce recall. |
| `stress_holdout_model_alias` | Match | `non_match` | Exact normalized model comparison misses a valid alias. |
| `stress_holdout_stale_ram` | Non-match | `match` | A stale or incorrect RAM-related field can still produce a false-positive merge. |

The previous stored holdout results came from an earlier baseline and must be replaced with the current output. To regenerate the JSON file using the present matcher:

```bash
python3 evaluation/product_matching/evaluate.py --split holdout > evaluation/product_matching/results_holdout.json
```

Older results remain accessible through Git history, but **must not be presented as current matcher performance**. The diagnostic numbers above are neither unbiased accuracy estimates nor evidence of live API performance.

## Review Changes and Remaining Limitations

The latest review changes include:

1. **Incomplete variant coverage:** Moved the one-sided missing-variant check before successful GTIN/MPN acceptance; added five regression tests.
2. **Accessory and bundle handling:** Expanded accessory recognition and introduced conservative handling for bundles/multipacks; added eight regression tests.
3. **Result reproducibility:** Re-evaluated the original 32-pair diagnostic set using the current matcher and documented the updated metrics.
4. **Evaluation integrity:** Explicitly reclassified the previously inspected holdout as diagnostic rather than independent.

Known limitations:

- Both listings may omit the same critical attribute; category-aware completeness requirements have not yet been established.
- Title-based accessory/bundle rules are heuristic and cannot guarantee comprehensive classification of retailer descriptions.
- Model aliases can cause false negatives.
- Inconsistent or stale RAM data can still cause false-positive matches.
- The current tests cover invented, structured examples rather than typical retailer API data quality.

## BGE-M3 and Reranker Feasibility

The [BAAI BGE-M3 model card](https://huggingface.co/BAAI/bge-m3) describes a multilingual embedding model supporting dense, sparse, and multi-vector retrieval. The [BGE project documentation](https://bge-model.com/bge/bge_m3) describes its architecture and deployment considerations. **BGE-M3 has not been installed or benchmarked for this project.**

**Potential benefit:** Embeddings may help discover candidate pairs despite model aliases, incomplete product names, and noisy retailer titles. A reranker may improve prioritization of candidates after retrieval.

**Key risk:** Semantic similarity does not establish exact SKU or offer equivalence. Closely related variants (for example, 128GB versus 256GB) may have similar descriptions while requiring a `non_match`. Identifier and variant-conflict checks should remain authoritative.

**P0 recommendation:** Retain the explainable identifier- and attribute-based baseline with explicit abstention and error logging. Do **not** introduce BGE-M3 as a P0 dependency based solely on synthetic data. Reconsider alias dictionaries, embedding retrieval, or reranking after representative independent retailer data identifies the dominant failure modes and allows precision, recall, latency, and memory comparisons.

## Next Steps for Independent Real-Retailer Evaluation

1. Confirm the canonical matching policy for color, condition, accessories, bundles, and offer-level versus parent-product grouping with PM/Data Science.
2. Obtain the finalized W1-12 `ProductOffer` schema and sample source payloads to build a transparent input adapter.
3. Source retailer records through authorized APIs, permitted datasets, or otherwise appropriately licensed sources. Record provenance, access restrictions, and rate limits.
4. Have product pairs independently labeled without using the matcher predictions as the labeling authority; include same-product, different-variant, accessory, bundle, and sparse-field cases.
5. Freeze the matcher and evaluation protocol **before** running the new independent dataset. Report precision, recall, F1, abstention coverage, and false-positive merges separately.
6. Consider aliases or embeddings only after reviewing actual real-data errors; benchmark any proposed improvement on a fresh untouched evaluation set.

The historical Web Data Commons product-matching corpus may provide a useful additional external benchmark, but it is **not equivalent to a live 2026 retailer API evaluation**. No independent real-retailer results are claimed in this report.

## Deliverable Locations

- Synthetic labeled dataset: `evaluation/product_pairs.jsonl`
- Base synthetic listings: `evaluation/product_matching/mock_products.json`
- Matcher and unit tests: `evaluation/product_matching/`
- Development evaluation: `evaluation/product_matching/results_development.json`
- Current diagnostic results: `evaluation/product_matching/results_holdout.json`
- Technical report: `docs/matching-baseline.md`

---

**Interpretation:** W1-25 has a functioning, regression-tested synthetic baseline. Independent real-retailer evaluation and final integration-policy decisions remain open.
