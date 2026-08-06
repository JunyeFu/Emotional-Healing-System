"""Validate the dispatch task registry without third-party dependencies."""

from __future__ import annotations

import csv
import pathlib
import sys


REGISTRY = pathlib.Path(__file__).with_name("05_可领取任务包.csv")
VALID_STATUSES = {"READY", "WAIT_DEP", "WAIT_DEP_EXTERNAL", "BLOCKED_EXTERNAL"}
EXPECTED_READY = {"F-01", "F-02", "F-03", "F-04"}


def main() -> int:
    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    errors: list[str] = []
    ids = [row["task_id"] for row in rows]
    known = set(ids)
    if len(ids) != len(known):
        errors.append("task_id values must be unique")

    for row in rows:
        task_id = row["task_id"]
        status = row["status"]
        if status not in VALID_STATUSES:
            errors.append(f"{task_id}: invalid status {status}")
        effort = int(row["effort_person_days"])
        if not 1 <= effort <= 5:
            errors.append(f"{task_id}: effort must be within 1..5 days")
        dependencies = {item for item in row["depends_on"].split("|") if item}
        missing = dependencies - known
        if missing:
            errors.append(f"{task_id}: unknown dependencies {sorted(missing)}")
        if task_id in dependencies:
            errors.append(f"{task_id}: self dependency")
        if status == "READY" and dependencies:
            errors.append(f"{task_id}: READY task has dependencies")

    graph = {
        row["task_id"]: {item for item in row["depends_on"].split("|") if item}
        for row in rows
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            errors.append(f"dependency cycle reaches {task_id}")
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in graph[task_id]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in graph:
        visit(task_id)

    ready = {row["task_id"] for row in rows if row["status"] == "READY"}
    if ready != EXPECTED_READY:
        errors.append(f"READY set is {sorted(ready)}, expected {sorted(EXPECTED_READY)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"PASS: {len(rows)} task packages; READY={','.join(sorted(ready))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
