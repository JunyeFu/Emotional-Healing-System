"""Validate dispatch tasks, learning references and forward composition."""

from __future__ import annotations

import csv
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).parent
REGISTRY = ROOT / "05_可领取任务包.csv"
RESOURCES = ROOT / "08_任务技能与国内学习资料_v1.0.md"
HANDBOOK = ROOT / "04_可领取树型任务包_v2.0.md"
VALID_STATUSES = {"READY", "WAIT_DEP", "WAIT_DEP_EXTERNAL", "BLOCKED_EXTERNAL"}
VALID_KINDS = {"FIXED", "TEMPLATE"}
VALID_PROFILES = {
    "P-DESIGN",
    "P-DEV",
    "P-HARDWARE",
    "P-ANALYSIS",
    "P-INTEGRATION",
    "P-RUN",
    "P-DELIVERY",
}
EXPECTED_READY = {"F-01", "F-02", "F-03", "F-04"}
EXPECTED_TEMPLATES = {"B-01", "B-02", "B-03"}
TERMINAL_TASK = "W-04"
WAVE_ORDER = {f"W{index}": index for index in range(7)}
REQUIRED_FIELDS = {
    "task_id",
    "parent_id",
    "wave",
    "domain",
    "title",
    "depends_on",
    "status",
    "kind",
    "effort_person_days",
    "process_profile",
    "skills",
    "learning_refs",
    "deliverables",
    "acceptance_criteria",
    "evidence_required",
    "completion_condition",
    "claimant",
    "branch",
    "reviewer",
}
UPGRADE_MARKERS = {
    "F-02": ("构念图", "注意连续性"),
    "R-01": ("必须匹配处理差异记录项矩阵", "四层跨模块语法"),
    "U-07": ("功能信息等价fixture", "条件差异遥测"),
    "U-08": ("非颜色唯一", "减少运动"),
    "A-03": ("阶段错误", "三层区分"),
    "W-01": ("双时间尺度", "正负结果分支"),
    "Q-01": ("跨模块可迁移审查",),
    "Q-02": ("阶段识别与三层区分任务", "可访问性路径"),
    "X-02": ("三类消融", "策略熵", "概率校准"),
    "G-03": ("U1至U5", "负面结果"),
    "A-05": ("模块异质性", "阶段错误"),
    "E-05": ("消融覆盖熵回退校准稳定性报告",),
    "G-04": ("策略审计配置", "负面结果分支"),
    "A-04": ("策略支持熵回退校准", "合成重建路径"),
    "W-02": ("双时间尺度", "设计规则与失败模式"),
    "W-03": ("Transparency and Openness", "独立复现日志"),
}


def split(value: str, separator: str = "|") -> list[str]:
    return [item.strip() for item in value.split(separator) if item.strip()]


def main() -> int:
    errors: list[str] = []
    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = set(reader.fieldnames or [])

    missing_fields = REQUIRED_FIELDS - fields
    if missing_fields:
        errors.append(f"registry missing fields {sorted(missing_fields)}")

    resource_text = RESOURCES.read_text(encoding="utf-8-sig")
    resource_ids = set(re.findall(r"^\| (L-[A-Z]+) \|", resource_text, flags=re.MULTILINE))
    handbook_text = HANDBOOK.read_text(encoding="utf-8-sig")

    ids = [row["task_id"] for row in rows]
    known = set(ids)
    if len(rows) != 51:
        errors.append(f"expected 51 registry entries, found {len(rows)}")
    if len(ids) != len(known):
        errors.append("task_id values must be unique")

    graph: dict[str, set[str]] = {}
    consumers: dict[str, set[str]] = {task_id: set() for task_id in known}
    for row in rows:
        task_id = row["task_id"]
        dependencies = set(split(row["depends_on"]))
        graph[task_id] = dependencies
        for dependency in dependencies & known:
            consumers[dependency].add(task_id)

        for field in (
            "parent_id",
            "wave",
            "domain",
            "title",
            "status",
            "kind",
            "effort_person_days",
            "process_profile",
            "skills",
            "learning_refs",
            "deliverables",
            "acceptance_criteria",
            "evidence_required",
            "completion_condition",
        ):
            if not row.get(field, "").strip():
                errors.append(f"{task_id}: empty required field {field}")

        if row["status"] not in VALID_STATUSES:
            errors.append(f"{task_id}: invalid status {row['status']!r}")
        if row["kind"] not in VALID_KINDS:
            errors.append(f"{task_id}: invalid kind {row['kind']!r}")
        if row["process_profile"] not in VALID_PROFILES:
            errors.append(f"{task_id}: invalid process profile {row['process_profile']!r}")
        if row["wave"] not in WAVE_ORDER:
            errors.append(f"{task_id}: invalid wave {row['wave']!r}")

        try:
            effort = int(row["effort_person_days"])
            if not 1 <= effort <= 5:
                errors.append(f"{task_id}: effort must be within 1..5 days")
        except ValueError:
            errors.append(f"{task_id}: effort is not an integer")

        expected_prefix = f"【{row['domain']}】"
        if not row["title"].startswith(expected_prefix):
            errors.append(f"{task_id}: title must start with {expected_prefix}")

        missing_dependencies = dependencies - known
        if missing_dependencies:
            errors.append(f"{task_id}: unknown dependencies {sorted(missing_dependencies)}")
        if task_id in dependencies:
            errors.append(f"{task_id}: self dependency")
        if row["status"] == "READY" and dependencies:
            errors.append(f"{task_id}: READY task has dependencies")
        if row["kind"] == "TEMPLATE" and row["status"] == "READY":
            errors.append(f"{task_id}: repeatable template cannot be READY")

        for dependency in dependencies & known:
            dependency_wave = next(item["wave"] for item in rows if item["task_id"] == dependency)
            if WAVE_ORDER.get(dependency_wave, 99) > WAVE_ORDER.get(row["wave"], -1):
                errors.append(f"{task_id}: depends on later-wave task {dependency}")

        refs = set(split(row["learning_refs"]))
        missing_refs = refs - resource_ids
        if missing_refs:
            errors.append(f"{task_id}: unknown learning references {sorted(missing_refs)}")
        if len(split(row["deliverables"], ";")) < 2:
            errors.append(f"{task_id}: fewer than two concrete deliverables")
        criteria = row["acceptance_criteria"]
        for marker in ("AC1", "AC2", "AC3"):
            if marker not in criteria:
                errors.append(f"{task_id}: missing acceptance marker {marker}")
        if len(split(row["evidence_required"], ";")) < 2:
            errors.append(f"{task_id}: fewer than two evidence items")
        if f"### {task_id} {row['title']}" not in handbook_text:
            errors.append(f"{task_id}: missing or stale handbook section")

        searchable = "|".join(row.values())
        for marker in UPGRADE_MARKERS.get(task_id, ()):
            if marker not in searchable:
                errors.append(f"{task_id}: missing IJHCI upgrade marker {marker!r}")

    template_ids = {row["task_id"] for row in rows if row["kind"] == "TEMPLATE"}
    if template_ids != EXPECTED_TEMPLATES:
        errors.append(f"template set is {sorted(template_ids)}, expected {sorted(EXPECTED_TEMPLATES)}")
    if len(rows) - len(template_ids) != 48:
        errors.append("expected 48 fixed task packages")

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

    def reaches_terminal(start: str) -> bool:
        pending = [start]
        seen: set[str] = set()
        while pending:
            current = pending.pop()
            if current == TERMINAL_TASK:
                return True
            if current in seen:
                continue
            seen.add(current)
            pending.extend(consumers[current] - seen)
        return False

    for task_id in known:
        if not reaches_terminal(task_id):
            errors.append(f"{task_id}: output does not reach final project handoff {TERMINAL_TASK}")

    ready = {row["task_id"] for row in rows if row["status"] == "READY"}
    if ready != EXPECTED_READY:
        errors.append(f"READY set is {sorted(ready)}, expected {sorted(EXPECTED_READY)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "PASS: 51 registry entries; fixed=48; templates=3; "
        f"READY={','.join(sorted(ready))}; terminal={TERMINAL_TASK}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
