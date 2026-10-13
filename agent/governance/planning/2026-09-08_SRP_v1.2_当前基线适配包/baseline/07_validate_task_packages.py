"""Validate dispatch tasks, learning references and forward composition."""

from __future__ import annotations

import csv
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).parent
REGISTRY = ROOT / "05_可领取任务包.csv"
RESOURCES = ROOT / "08_任务技能与国内学习资料_v1.0.md"
HANDBOOK = ROOT / "04_可领取树型任务包_v2.0.md"
PACKAGE_MAP = ROOT / "12_独立任务包文件映射_v1.0.json"
PACKAGE_OUTPUT = ROOT / "当前解锁独立任务包"
RELEASE_ROUTES = ROOT / "audit_upgrade" / "release_routes_v1.0.json"
MILESTONE_CONTRACT = ROOT / "audit_upgrade" / "task_milestones_v1.0.json"
MILESTONE_STATUS = ROOT / "audit_upgrade" / "task_milestone_status_v1.0.json"
VALID_STATUSES = {
    "READY", "IN_PROGRESS", "IN_REVIEW", "DONE",
    "WAIT_DEP", "WAIT_DEP_EXTERNAL", "BLOCKED_EXTERNAL",
}
PACKAGE_STATUSES = {"READY", "IN_PROGRESS", "IN_REVIEW"}
VALID_KINDS = {"FIXED", "TEMPLATE"}
VALID_MILESTONE_STATUSES = {
    "READY", "IN_PROGRESS", "IN_REVIEW", "WAIT_DEP", "DONE"
}
VALID_PROFILES = {
    "P-DESIGN",
    "P-DEV",
    "P-HARDWARE",
    "P-ANALYSIS",
    "P-INTEGRATION",
    "P-RUN",
    "P-DELIVERY",
}
EXPECTED_TEMPLATES = {"B-01", "B-02", "B-03"}
TERMINAL_TASK = "W-04"
WAVE_ORDER = {f"W{index}": index for index in range(7)}
REVIEW_PLACEHOLDERS = ("待复核", "待真实", "待签", "未签署", "pending", "tbd", "todo")
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
    "F-02": ("SCCI操纵检查", "条件中性四层理解题", "项目功能差异"),
    "G-01": ("528会话产能模型", "两周吞吐演练"),
    "G-02": ("机构密钥控制的HMAC联络去重表", "密钥与数据物理分离", "跨阶段重复审计"),
    "R-01": ("完整表示方案", "运动亮度复杂度偏心遮挡显著度"),
    "U-07": ("完整表示方案fixture", "六类视觉混杂报告"),
    "U-08": ("非颜色唯一", "减少运动"),
    "A-03": ("序数项目", "估计目标表", "Monte Carlo"),
    "W-01": ("2015至2026", "逐项增量与反证", "部署扩展降级分支"),
    "I-01": ("外部呈现延迟", "多小时压力"),
    "Q-01": ("独立重建", "四场景设计模式降称"),
    "Q-02": ("两条件逐题认知访谈", "目的与条件猜测"),
    "X-01": ("行为概率", "生成保管揭示角色"),
    "X-02": ("参与者分组", "离线策略价值", "有效样本量"),
    "X-03": ("同一scene_native构建", "PolicyDecision全字段"),
    "G-03": ("逐Gate估计目标表", "U1至U5及U8", "完整性清单"),
    "A-05": ("机会PF", "联合Gate2", "次要FDR"),
    "E-05": ("交叉拟合OPE", "有效样本量"),
    "G-04": ("含回退部署策略估计目标", "同一scene_native构建"),
    "A-04": ("估计目标", "次要FDR", "独立复现日志"),
    "W-02": ("完整提示表示主线", "条件式部署扩展", "主文补充材料预算"),
    "W-03": ("实时IJHCI作者说明快照", "数据可用性声明", "独立复现日志"),
    "A-06": ("阶段一主论文", "条件式阶段三", "范围关闭回执"),
}


def split(value: str, separator: str = "|") -> list[str]:
    return [item.strip() for item in value.split(separator) if item.strip()]


def unknown_dependencies(dependencies: set[str], known: set[str]) -> set[str]:
    return dependencies - known


def reviewer_is_placeholder(value: str) -> bool:
    reviewer = value.strip().casefold()
    return any(marker in reviewer for marker in REVIEW_PLACEHOLDERS)


def dependency_cycle_nodes(graph: dict[str, set[str]]) -> set[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            cycles.add(task_id)
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in graph[task_id] & graph.keys():
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in graph:
        visit(task_id)
    return cycles


def combined_dependency_graph(
    task_dependencies: dict[str, set[str]],
    milestones: list[dict[str, object]],
    completion_task: str,
) -> dict[str, set[str]]:
    graph = {node: set(dependencies) for node, dependencies in task_dependencies.items()}
    milestone_ids = {str(item["id"]) for item in milestones}
    for item in milestones:
        graph[str(item["id"])] = {str(value) for value in item.get("depends_on", [])}
    graph.setdefault(completion_task, set()).update(milestone_ids)
    return graph


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
    rows_by_id = {row["task_id"]: row for row in rows}
    milestone_contract = json.loads(MILESTONE_CONTRACT.read_text(encoding="utf-8"))
    milestone_status = json.loads(MILESTONE_STATUS.read_text(encoding="utf-8"))
    milestones = milestone_contract.get("milestones", [])
    milestone_ids = {str(item.get("id", "")) for item in milestones}
    milestone_statuses = milestone_status.get("statuses", {})
    known_nodes = known | milestone_ids
    node_status = {task_id: row["status"] for task_id, row in rows_by_id.items()}
    node_status.update({str(key): str(value) for key, value in milestone_statuses.items()})
    node_wave = {task_id: row["wave"] for task_id, row in rows_by_id.items()}
    node_wave.update({milestone_id: rows_by_id["A-03"]["wave"] for milestone_id in milestone_ids})
    if len(rows) != 59:
        errors.append(f"expected 59 registry entries, found {len(rows)}")
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
            maximum_effort = 6 if task_id in {"P-01", "V-04"} else 5
            if not 1 <= effort <= maximum_effort:
                errors.append(
                    f"{task_id}: effort must be within 1..{maximum_effort} days"
                )
        except ValueError:
            errors.append(f"{task_id}: effort is not an integer")

        expected_prefix = f"【{row['domain']}】"
        if not row["title"].startswith(expected_prefix):
            errors.append(f"{task_id}: title must start with {expected_prefix}")

        missing_dependencies = unknown_dependencies(dependencies, known_nodes)
        if missing_dependencies:
            errors.append(f"{task_id}: unknown dependencies {sorted(missing_dependencies)}")
        if task_id in dependencies:
            errors.append(f"{task_id}: self dependency")
        incomplete_dependencies = {
            dependency
            for dependency in dependencies & known_nodes
            if node_status.get(dependency) != "DONE"
        }
        if row["status"] in PACKAGE_STATUSES and incomplete_dependencies:
            errors.append(
                f"{task_id}: dispatch task has incomplete dependencies "
                f"{sorted(incomplete_dependencies)}"
            )
        if row["status"] == "WAIT_DEP" and dependencies and not incomplete_dependencies:
            errors.append(f"{task_id}: WAIT_DEP is stale because all dependencies are DONE")
        if row["status"] == "DONE":
            for field in ("claimant", "branch", "reviewer"):
                if not row[field].strip():
                    errors.append(f"{task_id}: DONE task has empty {field}")
            if reviewer_is_placeholder(row["reviewer"]):
                errors.append(f"{task_id}: DONE task has placeholder reviewer")
        if row["status"] == "READY" and any(
            row[field].strip() for field in ("claimant", "branch", "reviewer")
        ):
            errors.append(f"{task_id}: READY task must be unclaimed")
        if row["status"] in {"IN_PROGRESS", "IN_REVIEW"}:
            for field in ("claimant", "branch"):
                if not row[field].strip():
                    errors.append(f"{task_id}: {row['status']} task has empty {field}")
        if row["status"] == "IN_REVIEW" and not row["reviewer"].strip():
            errors.append(f"{task_id}: IN_REVIEW task has no review state")
        if row["status"] == "IN_REVIEW" and reviewer_is_placeholder(row["reviewer"]):
            errors.append(f"{task_id}: IN_REVIEW task has placeholder reviewer")
        if row["kind"] == "TEMPLATE" and row["status"] == "READY":
            errors.append(f"{task_id}: repeatable template cannot be READY")

        for dependency in dependencies & known_nodes:
            dependency_wave = node_wave[dependency]
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
    if len(rows) - len(template_ids) != 56:
        errors.append("expected 56 fixed task packages")

    if milestone_ids != {"A-03-SPEC", "A-03-REAL", "A-03-CAL"}:
        errors.append("A-03 milestone set is invalid")
    if set(milestone_statuses) != milestone_ids:
        errors.append("A-03 milestone status set is invalid")
    for item in milestones:
        milestone_id = str(item.get("id", ""))
        status = str(milestone_statuses.get(milestone_id, ""))
        dependencies = {str(value) for value in item.get("depends_on", [])}
        missing_dependencies = unknown_dependencies(dependencies, known_nodes)
        if missing_dependencies:
            errors.append(f"{milestone_id}: unknown dependencies {sorted(missing_dependencies)}")
        if status not in VALID_MILESTONE_STATUSES:
            errors.append(f"{milestone_id}: invalid status {status!r}")
        incomplete = {dependency for dependency in dependencies if node_status.get(dependency) != "DONE"}
        if status in {"READY", "IN_PROGRESS", "IN_REVIEW", "DONE"} and incomplete:
            errors.append(f"{milestone_id}: status {status} has incomplete dependencies {sorted(incomplete)}")
        if status == "WAIT_DEP" and dependencies and not incomplete:
            errors.append(f"{milestone_id}: WAIT_DEP is stale because all dependencies are DONE")
    if rows_by_id["A-03"]["status"] == "DONE" and any(
        node_status.get(milestone_id) != "DONE" for milestone_id in milestone_ids
    ):
        errors.append("A-03 cannot be DONE before all milestones are DONE")

    conditional_consumers: dict[str, set[str]] = {task_id: set() for task_id in known}
    if not RELEASE_ROUTES.is_file():
        errors.append("release route contract is missing")
    else:
        routes = json.loads(RELEASE_ROUTES.read_text(encoding="utf-8-sig"))
        for edge in routes.get("conditional_edges", []):
            source = edge.get("from")
            target = edge.get("to")
            if source not in known or target not in known:
                errors.append(f"release route has unknown edge {source!r} -> {target!r}")
            else:
                conditional_consumers[source].add(target)
                graph[target].add(source)
        if rows_by_id.get("A-06", {}).get("depends_on") != "A-05":
            errors.append("A-06 must have A-05 as its unconditional dependency")
        if rows_by_id.get("W-02", {}).get("depends_on") != "W-01|A-06":
            errors.append("W-02 must consume W-01 and A-06")

    completion_graph = combined_dependency_graph(graph, milestones, "A-03")
    for task_id in sorted(dependency_cycle_nodes(completion_graph)):
        errors.append(f"dependency cycle reaches {task_id}")

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
            pending.extend((consumers[current] | conditional_consumers[current]) - seen)
        return False

    for task_id in known:
        if not reaches_terminal(task_id):
            errors.append(f"{task_id}: output does not reach final project handoff {TERMINAL_TASK}")

    ready = {row["task_id"] for row in rows if row["status"] == "READY"}
    packaged_tasks = {row["task_id"] for row in rows if row["status"] in PACKAGE_STATUSES}
    done = {row["task_id"] for row in rows if row["status"] == "DONE"}

    if not PACKAGE_MAP.is_file():
        errors.append("independent task package mapping is missing")
    else:
        mapping = json.loads(PACKAGE_MAP.read_text(encoding="utf-8-sig"))
        mapped = set(mapping.get("tasks", {}))
        if mapped != packaged_tasks:
            errors.append(
                "independent package mapping set "
                f"{sorted(mapped)} does not match dispatch set {sorted(packaged_tasks)}"
            )

    if not PACKAGE_OUTPUT.is_dir():
        errors.append("independent READY task package output is missing")
    else:
        packaged = {path.name for path in PACKAGE_OUTPUT.iterdir() if path.is_dir()}
        if packaged != packaged_tasks:
            errors.append(
                "independent package directories "
                f"{sorted(packaged)} do not match dispatch set {sorted(packaged_tasks)}"
            )
        for task_id in packaged_tasks:
            for filename in ("TASK.md", "FILES.md", "package_manifest.json"):
                if not (PACKAGE_OUTPUT / task_id / filename).is_file():
                    errors.append(f"{task_id}: independent package missing {filename}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "PASS: 59 registry entries; fixed=56; templates=3; "
        f"DONE={','.join(sorted(done))}; READY={','.join(sorted(ready))}; "
        f"IN_REVIEW={','.join(sorted(row['task_id'] for row in rows if row['status'] == 'IN_REVIEW'))}; "
        f"terminal={TERMINAL_TASK}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
