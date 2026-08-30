"""Minimal harness for the RQ2 pilot (see docs/research/PILOT-TASK-SET.md).

Runs each PilotTask's scripted turns through `graph.invoke` directly
(bypassing `query_data.py:stream_graph_updates`'s reply-string-only return,
per EVALUATION-PROTOCOL.md section 4 step 1) so `assertions()` can score the
full final `TravelState`. Turns within a task share one accumulated
`messages`/`trip_constraints` pair across the task's own thread_id, mirroring
what `memory_store.py` does for a live session - but kept local to each task
run rather than going through the global `_STORE`, so pilot runs don't leak
state across tasks or across repeated harness invocations.

Model allocation per condition is switched by monkeypatching
`config.ORCHESTRATOR_MODEL`/`config.WORKER_MODEL` before each task, since
`llm.get_llm()` reads those attributes fresh on every call rather than
caching them at import time.
"""

import argparse
import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from langchain_core.messages import HumanMessage

import config
from graph.build_graph import graph
from graph.state import TravelState
from pilot.task_set import ALL_TASKS, PilotTask

# Per docs/03-llm-infra-decision.md: which tier each node's LLM call (if any)
# bills against, for the "cost per turn" metric in 08-evaluation-methodology.md.
ORCHESTRATOR_AGENTS = {"supervisor", "itinerary", "responder"}
WORKER_AGENTS = {"rag"}

CONDITIONS = {
    "tiered": None,  # no override - current config.py values
    "uniform_orchestrator": "orchestrator",  # both tiers use ORCHESTRATOR_MODEL
    "uniform_worker": "worker",  # both tiers use WORKER_MODEL
}


@contextmanager
def _model_condition(condition: str):
    override = CONDITIONS[condition]
    orig_orchestrator, orig_worker = config.ORCHESTRATOR_MODEL, config.WORKER_MODEL
    if override == "orchestrator":
        config.WORKER_MODEL = config.ORCHESTRATOR_MODEL
    elif override == "worker":
        config.ORCHESTRATOR_MODEL = config.WORKER_MODEL
    try:
        yield (config.ORCHESTRATOR_MODEL, config.WORKER_MODEL)
    finally:
        config.ORCHESTRATOR_MODEL, config.WORKER_MODEL = orig_orchestrator, orig_worker


def _empty_state(messages, thread_id: str, trip_constraints: dict) -> TravelState:
    return TravelState(
        messages=messages,
        thread_id=thread_id,
        trip_constraints=trip_constraints,
        flight_results=[],
        hotel_results=[],
        local_info_results=[],
        knowledge_context="",
        itinerary_draft=None,
        budget_summary=None,
        agent_scratchpad=[],
    )


def run_task(task: PilotTask, condition: str) -> dict:
    messages: list = []
    trip_constraints: dict = {}
    turn_records = []
    result = None
    error = None

    with _model_condition(condition) as (orchestrator_model, worker_model):
        for turn_text in task.turns:
            state = _empty_state(
                messages + [HumanMessage(content=turn_text)], task.thread_id, trip_constraints
            )
            t0 = time.perf_counter()
            try:
                result = graph.invoke(state, config={"configurable": {"thread_id": task.thread_id}})
            except Exception as exc:  # noqa: BLE001 - record and stop this task's turns
                error = f"{type(exc).__name__}: {exc}"
                break
            elapsed = time.perf_counter() - t0

            agents_visited = [e.get("agent") for e in result.get("agent_scratchpad", [])]
            turn_records.append({
                "hops": len(agents_visited),
                "agents_visited": agents_visited,
                "orchestrator_calls": sum(1 for a in agents_visited if a in ORCHESTRATOR_AGENTS),
                "worker_calls": sum(1 for a in agents_visited if a in WORKER_AGENTS),
                "elapsed_s": round(elapsed, 3),
            })
            messages = result["messages"]
            trip_constraints = result.get("trip_constraints", {})

    record = {
        "task_id": task.id,
        "condition": condition,
        "orchestrator_model": orchestrator_model,
        "worker_model": worker_model,
        "strata": task.strata,
        "turns": turn_records,
        "total_elapsed_s": round(sum(t["elapsed_s"] for t in turn_records), 3),
    }

    if error is not None:
        record["error"] = error
        record["passed"] = False
        record["failures"] = [error]
        return record

    failures = task.assertions(result)
    record["passed"] = not failures
    record["failures"] = failures
    return record


def run_all(tasks: list[PilotTask], condition: str) -> list[dict]:
    return [run_task(task, condition) for task in tasks]


def _print_summary(records: list[dict]) -> None:
    passed = sum(1 for r in records if r["passed"])
    print(f"\n{passed}/{len(records)} passed")
    for r in records:
        status = "PASS" if r["passed"] else "FAIL"
        hops = sum(t["hops"] for t in r["turns"])
        print(f"  [{status}] {r['task_id']:32s} hops={hops:2d} elapsed={r['total_elapsed_s']:6.2f}s")
        for f in r["failures"]:
            print(f"           - {f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--condition", choices=list(CONDITIONS) + ["all"], default="tiered",
        help="Model allocation condition to run (default: tiered, the current config.py values).",
    )
    parser.add_argument(
        "--tasks", default="",
        help="Comma-separated task ids to run (default: all 13 in ALL_TASKS).",
    )
    parser.add_argument("--out", default="", help="Write full JSON results to this path.")
    args = parser.parse_args()

    tasks = ALL_TASKS
    if args.tasks:
        wanted = set(args.tasks.split(","))
        tasks = [t for t in ALL_TASKS if t.id in wanted]
        missing = wanted - {t.id for t in tasks}
        if missing:
            sys.exit(f"Unknown task id(s): {sorted(missing)}")

    conditions = list(CONDITIONS) if args.condition == "all" else [args.condition]

    all_records = []
    for condition in conditions:
        print(f"\n=== condition: {condition} ===")
        records = run_all(tasks, condition)
        _print_summary(records)
        all_records.extend(records)

    if args.out:
        Path(args.out).write_text(json.dumps(all_records, indent=2))
        print(f"\nWrote {len(all_records)} record(s) to {args.out}")


if __name__ == "__main__":
    main()
