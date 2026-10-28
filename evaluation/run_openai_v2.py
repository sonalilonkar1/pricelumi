#!/usr/bin/env python3
"""Budget-conscious OpenAI Responses API runner for the 100-case ShopAgent v2 suite.

Offline by default. Only --run sends paid requests. Does not execute tools.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from build_prompts import main as build_inputs
from validate_suite import validate
from score_predictions import score, schema_for

ROOT = Path(__file__).resolve().parent
TASKS = ("intent", "tool", "grounding", "matching", "safety")
SCHEMAS = {"intent": "intent_v2.json", "grounding": "grounding_v2.json",
           "matching": "matching_v2.json", "safety": "safety_v2.json"}


def load_inputs():
    path = ROOT / "model_inputs.jsonl"
    if not path.exists():
        build_inputs()
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize_tools():
    tools = json.loads((ROOT / "schemas/tool_definitions.json").read_text())["tools"]
    return [{"type": "function", "name": x["name"], "description": x["description"],
             "parameters": x["parameters"], "strict": True} for x in tools]


def messages_for(case):
    task = case["task"]
    value = case["input"]
    if task in ("intent", "tool"):
        return value["messages"]
    return [{"role": "user", "content": json.dumps(value, ensure_ascii=False)}]


def request_payload(case, args):
    payload = {"model": args.model, "instructions": case["system"],
               "input": messages_for(case), "max_output_tokens": args.max_output_tokens}
    if args.reasoning != "omit":
        payload["reasoning"] = {"effort": args.reasoning}
    task = case["task"]
    if task == "tool":
        payload["tools"] = normalize_tools()
        payload["tool_choice"] = "auto"
        mode = "native_tool_call"
    elif task == "safety":
        # Nested freeform tool arguments in safety_v2 are not portable across strict
        # provider schema enforcement. Use JSON mode and validate locally instead.
        payload["text"] = {"format": {"type": "json_object"}}
        mode = "json_object_local_validation"
    else:
        schema = json.loads((ROOT / "schemas" / SCHEMAS[task]).read_text())
        payload["text"] = {"format": {"type": "json_schema", "name": f"shopagent_{task}_v2",
                                       "strict": True, "schema": schema}}
        mode = "strict_json_schema"
    return payload, mode


def normalize_response(response, task):
    if task == "tool":
        calls = []
        for item in response.output:
            if getattr(item, "type", None) == "function_call":
                try:
                    arguments = json.loads(item.arguments)
                except (TypeError, ValueError):
                    arguments = None
                calls.append({"name": item.name, "arguments": arguments})
        return {"tool_calls": calls}
    output = response.output_text or ""
    try:
        return json.loads(output)
    except (ValueError, TypeError):
        return None


def estimated_cost(usage, args):
    if not usage:
        return None
    inp = getattr(usage, "input_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or 0
    cached = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0) or 0
    return ((inp-cached)*args.input_rate + cached*args.cached_rate + out*args.output_rate)/1_000_000


def execute(client, case, args, gold):
    payload, mode = request_payload(case, args)
    row = {"case_id": case["case_id"], "task": case["task"], "split": case["split"],
           "model": args.model, "provider": "openai", "schema_mode": mode,
           "timestamp_utc": datetime.now(timezone.utc).isoformat(),
           "reasoning_effort": args.reasoning, "max_output_tokens": args.max_output_tokens,
           "status": "", "prediction": None, "schema_valid": False, "correct": False,
           "details": "", "error": "", "latency_seconds": None,
           "input_tokens": None, "output_tokens": None, "reasoning_tokens": None,
           "estimated_cost_usd": None, "raw_text": ""}
    start = time.perf_counter()
    try:
        response = client.responses.create(**payload)
        row["latency_seconds"] = round(time.perf_counter()-start, 3)
        row["status"] = response.status
        usage = response.usage
        if usage:
            row["input_tokens"] = usage.input_tokens
            row["output_tokens"] = usage.output_tokens
            row["reasoning_tokens"] = getattr(getattr(usage, "output_tokens_details", None), "reasoning_tokens", None)
            row["estimated_cost_usd"] = estimated_cost(usage, args)
        row["raw_text"] = response.output_text or ""
        row["prediction"] = normalize_response(response, case["task"])
        if response.status != "completed":
            row["details"] = f"response status: {response.status}"
        else:
            row["schema_valid"], row["correct"], row["details"] = score(case["task"], gold, row["prediction"])
    except Exception as exc:
        row["latency_seconds"] = round(time.perf_counter()-start, 3)
        row["error"] = f"{type(exc).__name__}: {str(exc)[:350]}"
        row["details"] = "provider request failed"
    return row


def save(rows, directory, args, dataset_hash):
    directory.mkdir(parents=True, exist_ok=True)
    # Keep both raw per-request evidence and normalized predictions. Do not publish
    # either without checking for sensitive data in real future fixtures.
    (directory/"runs.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows))
    (directory/"predictions.jsonl").write_text("".join(json.dumps({"case_id":r["case_id"],"prediction":r["prediction"]},ensure_ascii=False)+"\n" for r in rows))
    by_task = {}
    for row in rows:
        by_task.setdefault(row["task"], []).append(row)
    summary = []
    for task in TASKS:
        group = by_task.get(task, [])
        if not group: continue
        lat = sorted(r["latency_seconds"] for r in group if r["latency_seconds"] is not None and not r["error"])
        costs = [r["estimated_cost_usd"] for r in group if r["estimated_cost_usd"] is not None]
        p95 = lat[min(len(lat)-1, max(0, (95*len(lat)+99)//100-1))] if lat else None
        summary.append({"task":task, "submitted":len(group),
                        "correct":sum(bool(r["correct"]) for r in group),
                        "schema_valid":sum(bool(r["schema_valid"]) for r in group),
                        "errors":sum(bool(r["error"]) for r in group),
                        "accuracy_submitted_pct":round(100*sum(bool(r["correct"]) for r in group)/len(group),1),
                        "p50_latency_seconds":median(lat) if lat else None,
                        "p95_latency_seconds":p95,
                        "estimated_cost_usd":round(sum(costs),8)})
    with (directory/"summary.csv").open("w",newline="") as f:
        writer = csv.DictWriter(f,fieldnames=list(summary[0]))
        writer.writeheader(); writer.writerows(summary)
    (directory/"failures.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows if not r["correct"]))
    metadata = {"model":args.model,"dataset_version":"v2.0", "dataset_sha256":dataset_hash,
                "reasoning_effort":args.reasoning,"max_output_tokens":args.max_output_tokens,
                "price_per_million": {"input":args.input_rate,"cached":args.cached_rate,"output":args.output_rate},
                "calls":len(rows),"estimated_cost_usd":round(sum(r["estimated_cost_usd"] or 0 for r in rows),8),
                "notes":"Partial accuracy uses submitted cases only. Results are preliminary pending label review."}
    (directory/"metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="OpenAI v2 ShopAgent benchmark; offline by default")
    parser.add_argument("--run", action="store_true", help="Actually call paid OpenAI API")
    parser.add_argument("--model", default="gpt-5-nano")
    parser.add_argument("--task", choices=[*TASKS,"all"], default="all")
    parser.add_argument("--split", choices=["development","holdout","all"], default="development")
    parser.add_argument("--confirm-holdout", action="store_true", help="Explicitly unlock final holdout evaluation")
    parser.add_argument("--limit", type=int, default=1, help="Maximum cases per task; default 1")
    parser.add_argument("--all-cases", action="store_true", help="All cases in selected split")
    parser.add_argument("--max-calls", type=int, default=5, help="Maximum requests this invocation")
    parser.add_argument("--max-spend", type=float, default=0.10, help="Estimated USD spending threshold")
    parser.add_argument("--input-rate", type=float, default=None, help="USD per 1M input tokens")
    parser.add_argument("--cached-rate", type=float, default=None, help="USD per 1M cached input tokens")
    parser.add_argument("--output-rate", type=float, default=None, help="USD per 1M output tokens")
    parser.add_argument("--max-output-tokens", type=int, default=1200)
    parser.add_argument("--reasoning", choices=["omit","minimal","low","medium","high"], default="minimal")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--resume", action="store_true", help="Skip cases already present in output/runs.jsonl")
    args = parser.parse_args(argv)
    # This public package contains only development cases; private holdout is unavailable.
    if args.split in ("holdout", "all"):
        parser.error("Holdout cases are private and not included in this public package")
    if args.split in ("holdout", "all") and not args.confirm_holdout:
        parser.error("Holdout locked: add --confirm-holdout only after freezing prompts and labels.")
    if args.max_calls < 1 or args.limit < 1 or args.max_spend <= 0 or args.max_output_tokens < 1:
        parser.error("Use positive --limit, --max-calls, --max-spend, and --max-output-tokens.")
    data = validate(verbose=False)
    cases = load_inputs()
    gold = {c["id"]:(task,c) for task,group in data.items() for c in group}
    selected = [c for c in cases if (args.task == "all" or c["task"]==args.task)
                and (args.split == "all" or c["split"]==args.split)]
    if not args.all_cases:
        counters = {}
        limited=[]
        for c in selected:
            if counters.get(c["task"],0) < args.limit:
                limited.append(c)
                counters[c["task"]]=counters.get(c["task"],0)+1
        selected=limited
    if len(selected) > args.max_calls:
        parser.error(f"{len(selected)} calls requested, exceeding --max-calls={args.max_calls}. Increase explicitly.")
    digest = hashlib.sha256((ROOT/"model_inputs.jsonl").read_bytes()).hexdigest()
    output = args.output or ROOT/"results"/re.sub(r"[^a-zA-Z0-9_.-]", "_", args.model)/args.split
    existing = []
    runs_path = output / "runs.jsonl"

    if runs_path.exists():
        if args.run and not args.resume:
            parser.error(
                f"{runs_path} exists; choose a different --output or use --resume"
            )

        if args.resume:
            metadata_path = output / "metadata.json"
            if not metadata_path.exists():
                parser.error(
                    f"{metadata_path} is missing; cannot safely resume this run"
                )

            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            if meta.get("model") != args.model or meta.get("dataset_sha256") != digest:
                parser.error(
                    "Existing results use a different model or dataset; use a new output directory"
                )
            if (meta.get("reasoning_effort") != args.reasoning
                    or meta.get("max_output_tokens") != args.max_output_tokens):
                parser.error(
                    "Existing results use different reasoning/output settings; use a new output directory"
                )

            existing = [
                json.loads(line)
                for line in runs_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

    prior = {r["case_id"] for r in existing}
    pending = [c for c in selected if c["case_id"] not in prior]
    print(f"Dataset v2.0 | {len(selected)} selected | {len(pending)} pending | split={args.split} | model={args.model}")
    if not args.run:
        print("DRY RUN: no API calls and no charges.")
        for c in pending: print(f"  {c['case_id']} [{c['task']}] {c['split']}")
        return 0
    if not os.getenv("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY missing; set it in your shell, not source code")
    if any(v is None or v < 0 for v in (args.input_rate,args.cached_rate,args.output_rate)):
        parser.error("Provide nonnegative --input-rate --cached-rate --output-rate from official pricing")
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=45.0, max_retries=0)
    spent = sum((r.get("estimated_cost_usd") or 0) for r in existing)
    rows = existing[:]
    for case in pending:
        payload,_ = request_payload(case,args)
        prompt_len = len(json.dumps(payload,ensure_ascii=False))
        conservative_in = max(1500, prompt_len//2)
        reserve = (conservative_in*max(args.input_rate,args.cached_rate)+args.max_output_tokens*args.output_rate)/1_000_000
        if spent + reserve > args.max_spend:
            print(f"STOP: next-call reserve ${reserve:.6f} exceeds remaining local budget")
            break
        row = execute(client,case,args,gold[case["case_id"]][1])
        rows.append(row)
        spent += row["estimated_cost_usd"] if row["estimated_cost_usd"] is not None else reserve
        print(f"{case['case_id']} {case['task']}: correct={row['correct']} schema={row['schema_valid']} "
              f"latency={row['latency_seconds']}s estimated_cost={row['estimated_cost_usd']} error={row['error'][:90]}")
        if "insufficient_quota" in row["error"] or "credit_balance_exhausted" in row["error"]:
            print("STOP: insufficient API credits")
            break
        if "BadRequestError" in row["error"] or "AuthenticationError" in row["error"]:
            print("STOP: provider rejected request; inspect error before retrying")
            break
    if rows:
        summary=save(rows,output,args,digest)
        print("Summary (submitted cases only):")
        for x in summary: print(x)
        print(f"Estimated cumulative cost ${spent:.6f}. Output: {output}")
        print("Provider billing is authoritative; local budget guard is not a hard cap.")
    else:
        print("No paid calls made.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
