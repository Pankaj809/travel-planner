"""Aggregate `pilot/results/*.json` (see harness.py) into comparison tables
across model-allocation conditions, per EVALUATION-PROTOCOL.md section 4.

This pilot's n=13 is too small for the protocol's proportion tests (section
5) - this script reports descriptive tables only, not significance tests.
"""

import json
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
CONDITIONS = ["tiered", "uniform_orchestrator", "uniform_worker"]
CONDITION_LABEL = {
    "tiered": "Tiered (orchestrator/worker split)",
    "uniform_orchestrator": "Uniform-large (orchestrator model everywhere)",
    "uniform_worker": "Uniform-small (worker model everywhere)",
}


def load(condition: str) -> list[dict]:
    return json.loads((RESULTS_DIR / f"{condition}.json").read_text())


def per_task_table(all_records: dict[str, list[dict]]) -> str:
    task_ids = [r["task_id"] for r in all_records["tiered"]]
    lines = ["| Task | " + " | ".join(CONDITION_LABEL[c] for c in CONDITIONS) + " |",
             "|---|" + "---|" * len(CONDITIONS)]
    by_condition = {c: {r["task_id"]: r for r in all_records[c]} for c in CONDITIONS}
    for tid in task_ids:
        cells = []
        for c in CONDITIONS:
            r = by_condition[c][tid]
            mark = "PASS" if r["passed"] else "FAIL(" + ";".join(r["failures"]) + ")"
            cells.append(mark)
        lines.append(f"| {tid} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def summary_table(all_records: dict[str, list[dict]]) -> str:
    lines = ["| Condition | Pass rate | Total hops | Orchestrator calls | Worker calls | Total elapsed (s) |",
             "|---|---|---|---|---|---|"]
    for c in CONDITIONS:
        records = all_records[c]
        passed = sum(1 for r in records if r["passed"])
        total_hops = sum(t["hops"] for r in records for t in r["turns"])
        orch_calls = sum(t["orchestrator_calls"] for r in records for t in r["turns"])
        worker_calls = sum(t["worker_calls"] for r in records for t in r["turns"])
        elapsed = sum(r["total_elapsed_s"] for r in records)
        lines.append(
            f"| {CONDITION_LABEL[c]} | {passed}/{len(records)} | {total_hops} | "
            f"{orch_calls} | {worker_calls} | {elapsed:.1f} |"
        )
    return "\n".join(lines)


def failure_overlap(all_records: dict[str, list[dict]]) -> str:
    fail_sets = {
        c: {r["task_id"] for r in all_records[c] if not r["passed"]} for c in CONDITIONS
    }
    common = set.intersection(*fail_sets.values())
    lines = [f"Failing in all {len(CONDITIONS)} conditions ({len(common)}): "
             + ", ".join(sorted(common))]
    for c in CONDITIONS:
        only = fail_sets[c] - common
        if only:
            lines.append(f"Failing only in {c}: {', '.join(sorted(only))}")
    return "\n".join(lines)


def main() -> None:
    all_records = {c: load(c) for c in CONDITIONS}
    print("## Per-task result by condition\n")
    print(per_task_table(all_records))
    print("\n## Summary\n")
    print(summary_table(all_records))
    print("\n## Failure overlap\n")
    print(failure_overlap(all_records))


if __name__ == "__main__":
    main()
