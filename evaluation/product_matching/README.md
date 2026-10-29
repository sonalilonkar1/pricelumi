# W1-25 — Product matching evaluation

This is an **offline, standard-library-only Python baseline**. It does not contact retailer APIs, deploy a model, or require credentials.

## What is here?

- `../product_pairs.jsonl`: official W1-25 deliverable — labeled product pairs with `development` and `holdout` splits.
- `mock_products.json`: 48 **invented** product listings designed to resemble different retailer naming conventions. They are not real Walmart, Best Buy, or eBay responses.
- `baseline.py`: three-way matching decision (`match`, `non_match`, `uncertain`) and reason.
- `evaluate.py`: precision/recall/F1 and false-positive/false-negative examples.
- `validate_dataset.py`: dataset checks, GTIN checksum checks and product-family split separation.
- `test_baseline.py`: unit tests of deterministic behavior and non-match safeguards.
- `results_holdout.json`: evaluation snapshot, produced by `evaluate.py`.
- `../../docs/matching-baseline.md`: results, error analysis and embedding feasibility recommendation.

## Run from the repository root

```bash
python evaluation/product_matching/validate_dataset.py
python -m unittest discover -s evaluation/product_matching -p 'test_*.py' -v
python evaluation/product_matching/evaluate.py --split development
python evaluation/product_matching/evaluate.py --split holdout --output evaluation/product_matching/results_holdout.json
```

Python **3.10+** recommended. No package installation is required.

## Labeling policy (provisional)

Label `1` when the two offers represent the same **purchasable variant and condition**; otherwise label `0`. Changed capacity, model, connector, disc edition, color, condition or a different item/accessory can be a non-match. **This is an assumption for W1-25**, not a confirmed product policy: review condition/color/bundles with the team.

`stress_case: true` marks extra manually constructed edge pairs, some deliberately containing stale/missing normalized fields. These pair-only perturbations are not separate entries in `mock_products.json`.

## Evaluation design and limitations

- The `development` and `holdout` splits have **disjoint product families**, reducing leakage from repeat listings.
- `uncertain` is **not automatically merged**, and counts as a negative prediction for binary precision/recall. We also report automatic-decision coverage and the uncertain examples.
- All records, prices, GTINs and MPNs are **synthetic** (GTINs have valid checksums but do not claim real allocation; MPNs use `SYN-` prefixes).
- The dataset was authored to test a baseline and is **not representative of production traffic**. Do **not** claim field-performance estimates for actual retailer APIs from these results.
- Additional live API/retailer mock samples should be labeled independently after the ProductOffer schema is available.

## Schema adaptation

The input shape is provisional: `id`, `retailer`, `title`, `brand`, `model`, `gtin`, `mpn`, `variants` and `price_usd`. The matcher **only** reads brand, model, GTIN, MPN and variants. Adapt a finalized `ProductOffer` via a small mapper instead of embedding backend schema assumptions in matching logic.
