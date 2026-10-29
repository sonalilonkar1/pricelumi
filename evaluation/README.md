# ShopAgent / Pricelumi — Public Development Evaluation (70 cases)

This directory contains **only the 70 development cases** from the private 100-case v2 benchmark. The **30 holdout cases, their prompts, and their expected answers are intentionally excluded**.

## Offline checks (no API charges)

```bash
python3 validate_suite.py
python3 -m unittest -v test_suite.py test_runner_v2.py
python3 build_prompts.py
python3 run_openai_v2.py --task all
```

The generator creates `model_inputs.jsonl` with only the 70 development cases. Do not copy `model_inputs.jsonl` from the private master afterward.

## Running paid OpenAI evaluation

Set `OPENAI_API_KEY` in the environment (never commit it), confirm current model rates, and pass `--run` with `--split development`, `--max-calls`, and `--max-spend`. The runner is offline by default. See `run_openai_v2.py --help`.

## Results and provenance

- The audited `reports/W1-09_BENCHMARK_REPORT.md` describes a prior run against the **private full 100-case suite's 70 development cases**. Its SHA-256 hashes refer to the private full-suite files, so hashes of this public subset will differ.
- Historical raw results and the original full-suite inputs are not included. Keep them private for audit/reproduction with the original hashes.
- This public package supports new 70-case development runs. It cannot run the private holdout split.
- Independent gold-label review is pending. First-action tool-choice tests do not execute tools; safety tests do not prove backend checkout authorization.
