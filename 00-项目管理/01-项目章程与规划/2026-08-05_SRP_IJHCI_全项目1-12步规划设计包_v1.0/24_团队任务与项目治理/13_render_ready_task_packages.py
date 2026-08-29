"""Render standalone packages for READY and IN_REVIEW tasks."""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import runpy
import shutil


ROOT = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[3]
REGISTRY = ROOT / "05_可领取任务包.csv"
MAPPING = ROOT / "12_独立任务包文件映射_v1.0.json"
HANDBOOK_RENDERER = ROOT / "10_render_task_handbook.py"
OUTPUT = ROOT / "当前解锁独立任务包"
TEXT_SUFFIXES = {
    ".cs", ".csv", ".gitattributes", ".json", ".md", ".ps1", ".py", ".sha256", ".txt"
}
TEXT_NAMES = {".gitattributes"}
PACKAGE_STATUSES = {"READY", "IN_REVIEW"}


def canonical_content(path: pathlib.Path) -> bytes:
    content = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES or path.name.lower() in TEXT_NAMES:
        content = content.replace(b"\r\n", b"\n")
        content = b"\n".join(line.rstrip(b" \t") for line in content.split(b"\n"))
    return content


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(canonical_content(path)).hexdigest().upper()


def split_items(value: str, separator: str = ";") -> list[str]:
    return [item.strip() for item in value.split(separator) if item.strip()]


def render_checklist(items: list[str], results: object, default_checked: bool) -> list[str]:
    if results is None:
        marker = "x" if default_checked else " "
        return [f"- [{marker}] {item}" for item in items]
    if not isinstance(results, list) or len(results) != len(items):
        raise ValueError("checklist results must be a list matching the rendered item count")
    lines = []
    for item, result in zip(items, results, strict=True):
        normalized = str(result).strip().upper()
        marker = "x" if normalized == "PASS" else " "
        suffix = "" if normalized == "PASS" else f" — `{normalized}`"
        lines.append(f"- [{marker}] {item}{suffix}")
    return lines


def safe_source(relative: str) -> pathlib.Path:
    path = (PROJECT_ROOT / relative).resolve()
    if PROJECT_ROOT not in path.parents or not path.is_file():
        raise ValueError(f"invalid source file: {relative}")
    return path


def safe_working_path(relative: str) -> pathlib.Path:
    path = (PROJECT_ROOT / relative).resolve()
    if PROJECT_ROOT not in path.parents or not path.exists():
        raise ValueError(f"invalid working path: {relative}")
    return path


def task_markdown(
    row: dict[str, str],
    resources: dict[str, tuple[str, str]],
    process_profiles: dict[str, tuple[str, ...]],
    task_map: dict[str, object],
) -> str:
    dependencies = row["depends_on"].replace("|", "、") or "无"
    refs = []
    for ref_id in row["learning_refs"].split("|"):
        title, url = resources[ref_id]
        refs.append(f"- [{ref_id} {title}]({url})")

    lines = [
        f"# {row['task_id']} {row['title']}",
        "",
        "> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。",
        "",
        "## 领取登记",
        "",
        f"- 领取人：{row['claimant'] or '未领取'}",
        f"- 分支：`{row['branch'] or 'codex/<task-id>-<short-name>'}`",
        f"- 第二复核人：{row['reviewer'] or '未指定'}",
        f"- 领取时间：{'历史登记未记录；当前不得重复领取' if row['claimant'] else '未领取'}",
        "",
        "## 任务边界",
        "",
        f"- 领域：{row['domain']}",
        f"- 波次：{row['wave']}",
        f"- 状态：`{row['status']}`",
        f"- 类型：{row['kind']}",
        f"- 预计工作量：{row['effort_person_days']}人日",
        f"- 前置依赖：{dependencies}",
        f"- 所需技能：{row['skills']}",
        "- 涉及文件与工作目录：见[FILES.md](FILES.md)",
        "",
        "## 学习资料",
        "",
        *refs,
        "",
        "## 交付物",
        "",
    ]
    lines.extend(f"- {item}" for item in split_items(row["deliverables"]))
    lines.extend(["", "## 四阶段过程", ""])
    lines.extend(
        f"{index}. {step}。"
        for index, step in enumerate(process_profiles[row["process_profile"]], start=1)
    )
    lines.extend(["", "## 验收要求", ""])
    lines.extend(
        render_checklist(
            split_items(row["acceptance_criteria"], "；"),
            task_map.get("acceptance_results"),
            row["status"] == "IN_REVIEW",
        )
    )
    lines.extend(["", "## 必需证据", ""])
    lines.extend(
        render_checklist(
            split_items(row["evidence_required"]),
            task_map.get("evidence_results"),
            row["status"] == "IN_REVIEW",
        )
    )
    if row["status"] == "IN_REVIEW":
        source_files = [str(item) for item in task_map["source_files"]]
        evidence_paths = [
            item
            for item in source_files
            if "技术验收记录" in item
            or "/evidence/" in item
            or "/fixtures/golden/" in item
        ]
        completion = [
            "- 实际改动文件：见`FILES.md`列出的项目权威路径",
            f"- 验证命令与结果：技术候选已完成；模型复核状态`{task_map.get('model_review_status', 'PENDING')}`",
            "- 证据路径：" + "；".join(f"`{item}`" for item in evidence_paths),
            f"- commit：`{task_map.get('implementation_commit', 'PENDING_FIX_COMMIT')}`",
            f"- push目标：`origin/{row['branch']}`",
            "- 剩余风险：真实团队第二人签署及任务文档列明的外部边界仍开放",
        ]
    else:
        completion = [
            "- 实际改动文件：",
            "- 验证命令与结果：",
            "- 证据路径：",
            "- commit：",
            "- push目标：",
            "- 剩余风险：",
        ]
    lines.extend(
        [
            "",
            "## 完成条件",
            "",
            row["completion_condition"],
            "",
            "完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。",
            "",
            "## 完成回填",
            "",
            *completion,
            "",
        ]
    )
    return "\n".join(lines)


def files_markdown(
    task_id: str,
    copied: list[dict[str, object]],
    working_paths: list[str],
) -> str:
    lines = [
        f"# {task_id} 涉及文件",
        "",
        "> `inputs/`是领取时输入快照，只用于离线阅读和核对。不要在快照中实现；应修改下列项目权威路径。",
        "",
        "## 输入文件",
        "",
        "| 项目权威路径 | 包内快照 | SHA-256 |",
        "|---|---|---|",
    ]
    for item in copied:
        source = str(item["source_path"])
        package_path = str(item["package_path"])
        lines.append(
            f"| [{source}](D:/Agent/03-SRP/{source}) | [{package_path}]({package_path}) | `{item['sha256']}` |"
        )
    lines.extend(["", "## 实现工作目录", ""])
    for relative in working_paths:
        lines.append(f"- [{relative}](D:/Agent/03-SRP/{relative})")
    lines.extend(
        [
            "",
            "## 权威规则",
            "",
            "- 开始前读取项目根目录`AGENTS.md`并运行`git status --short`。",
            "- 输入文件变化后重新生成任务包；哈希不一致的旧包不得继续分发。",
            "- 文本快照统一为LF并移除行尾空白；二进制快照保持原始字节。",
            "- 快照保留原文内容，其内部相对链接可能仍指向原目录；需要追踪链接时从上表打开项目权威文件。",
            "- 大型工程、缓存、构建结果和个人配置不复制进任务包。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    package_rows = {
        row["task_id"]: row for row in rows if row["status"] in PACKAGE_STATUSES
    }
    mapping = json.loads(MAPPING.read_text(encoding="utf-8-sig"))
    task_maps = mapping["tasks"]
    if set(package_rows) != set(task_maps):
        raise ValueError(
            f"dispatch set {sorted(package_rows)} does not match mapping {sorted(task_maps)}"
        )

    renderer = runpy.run_path(str(HANDBOOK_RENDERER))
    resources = renderer["parse_resources"]()
    process_profiles = renderer["PROCESS_PROFILES"]

    build = ROOT / ".ready-task-packages-build"
    if build.exists():
        shutil.rmtree(build)
    build.mkdir()

    registry_hash = sha256(REGISTRY)
    summary_rows = []
    for task_id in sorted(package_rows):
        row = package_rows[task_id]
        task_map = task_maps[task_id]
        package_dir = build / task_id
        inputs_dir = package_dir / "inputs"
        inputs_dir.mkdir(parents=True)

        copied: list[dict[str, object]] = []
        for index, relative in enumerate(task_map["source_files"], start=1):
            source = safe_source(relative)
            snapshot_name = f"{index:02d}_{source.name}"
            destination = inputs_dir / snapshot_name
            if source.suffix.lower() in TEXT_SUFFIXES:
                destination.write_bytes(canonical_content(source))
            else:
                shutil.copy2(source, destination)
            copied.append(
                {
                    "source_path": relative,
                    "package_path": f"inputs/{snapshot_name}",
                    "sha256": sha256(source),
                    "size_bytes": destination.stat().st_size,
                }
            )

        for relative in task_map["working_paths"]:
            safe_working_path(relative)

        (package_dir / "TASK.md").write_text(
            task_markdown(row, resources, process_profiles, task_map), encoding="utf-8"
        )
        (package_dir / "FILES.md").write_text(
            files_markdown(task_id, copied, task_map["working_paths"]), encoding="utf-8"
        )
        manifest = {
            "package_schema_version": "1.0",
            "hash_policy": "sha256_lf_no_trailing_ws_text_v1",
            "task_id": task_id,
            "status": row["status"],
            "registry_sha256": registry_hash,
            "source_files": copied,
            "working_paths": task_map["working_paths"],
        }
        (package_dir / "package_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        summary_rows.append(
            f"| {task_id} | {row['status']} | {row['title']} | {row['effort_person_days']}人日 | [{task_id}/TASK.md]({task_id}/TASK.md) |"
        )

    readme = [
        "# 当前解锁独立任务包",
        "",
        "> 本目录由`13_render_ready_task_packages.py`确定性生成，包含可领取的`READY`任务和等待复核的`IN_REVIEW`任务。只有`READY`且领取人为空的任务可以领取。",
        "> 每个包均含任务说明、涉及文件清单、输入快照和哈希清单；状态变化后必须重新生成并校验。",
        "",
        "| 任务 | 状态 | 名称 | 工作量 | 入口 |",
        "|---|---|---|---:|---|",
        *summary_rows,
        "",
    ]
    (build / "README.md").write_text("\n".join(readme), encoding="utf-8")

    if OUTPUT.exists():
        if OUTPUT.parent != ROOT or OUTPUT.name != mapping["output_directory"]:
            raise ValueError(f"refusing to replace unexpected output: {OUTPUT}")
        shutil.rmtree(OUTPUT)
    build.rename(OUTPUT)
    print(f"WROTE: {OUTPUT.name}; DISPATCH={','.join(sorted(package_rows))}")


if __name__ == "__main__":
    main()
