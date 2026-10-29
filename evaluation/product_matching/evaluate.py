"""Evaluate W1-25 matching baseline against explicitly labeled JSONL pairs."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from baseline import match_products


def evaluate(dataset: Path, split: str) -> dict:
    counts = Counter()
    examples: list[dict] = []
    decisions = Counter()
    pair_ids = set()
    with dataset.open(encoding="utf-8") as file:
        for line_num, line in enumerate(file, start=1):
            if not line.strip():
                continue
            sample = json.loads(line)
            if sample.get("split") != split and split != "all":
                continue
            pid, label = sample.get("pair_id"), sample.get("label")
            if not pid or pid in pair_ids:
                raise ValueError(f"Missing/duplicate pair ID near line {line_num}")
            if type(label) is not int or label not in (0, 1):
                raise ValueError(f"Invalid binary label at line {line_num}")
            if sample.get("data_origin") != "synthetic":
                raise ValueError(f"Unexpected provenance at line {line_num}")
            pair_ids.add(pid)
            result = match_products(sample["product_a"], sample["product_b"])
            decisions[result.decision] += 1
            # "uncertain" means do not automatically merge. It is a negative
            # decision in the automatic-match classifier; report abstention.
            predicted = int(result.decision == "match")
            outcome = ("tp" if predicted else "fn") if label else ("fp" if predicted else "tn")
            counts[outcome] += 1
            if predicted != label or result.decision == "uncertain":
                examples.append({
                    "pair_id": pid, "true_label": label,
                    "prediction": result.decision, "reason": result.reason,
                    "evidence": result.evidence, "error_type": outcome if predicted != label else None,
                })
    if not pair_ids:
        raise ValueError(f"No pairs for split: {split}")
    tp, fp, fn, tn = (counts[k] for k in ("tp", "fp", "fn", "tn"))
    precision = tp/(tp+fp) if tp+fp else 0.0
    recall = tp/(tp+fn) if tp+fn else 0.0
    f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {
        "split":split, "total_pairs":len(pair_ids),
        "confusion_matrix":{"tp":tp,"fp":fp,"fn":fn,"tn":tn},
        "precision":round(precision,4), "recall":round(recall,4),
        "f1":round(f1,4),
        "automatic_match_coverage":round((decisions["match"]+decisions["non_match"])/len(pair_ids),4),
        "decisions":dict(decisions), "errors_and_uncertain":examples,
        "caveat":"Entirely synthetic data; not evidence of live-API performance.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",type=Path,default=Path(__file__).resolve().parents[1]/"product_pairs.jsonl")
    parser.add_argument("--split",choices=["development","holdout","all"],default="holdout")
    parser.add_argument("--output",type=Path,default=None)
    args=parser.parse_args()
    result=evaluate(args.dataset,args.split)
    text=json.dumps(result,indent=2)+"\n"
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text,encoding="utf-8")

if __name__ == "__main__":
    main()
