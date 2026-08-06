"""Render the human-readable task handbook from the CSV registry."""

from __future__ import annotations

import csv
import pathlib
import re


ROOT = pathlib.Path(__file__).parent
REGISTRY = ROOT / "05_可领取任务包.csv"
RESOURCES = ROOT / "08_任务技能与国内学习资料_v1.0.md"
OUTPUT = ROOT / "04_可领取树型任务包_v2.0.md"

PROCESS_PROFILES = {
    "P-DESIGN": (
        "核对冻结依据、构念、权限和不承担项",
        "形成候选材料、配置或治理台账",
        "用双人审查、合成样例或检查表迭代",
        "冻结版本、记录差异并向下游交接",
    ),
    "P-DEV": (
        "读取依赖制品并先建立失败测试或golden fixture",
        "只在所属模块内实现最小完整纵向能力",
        "运行正常、异常、重连或权限负测试",
        "整理代码、文档、证据并提交第二人验收",
    ),
    "P-HARDWARE": (
        "核对设备、序列号、官方协议和采样配置",
        "实现连接、采集、时间戳、状态和重连",
        "完成短测、故障注入和30分钟真机稳定性运行",
        "归档原始日志、配置、统计和已知限制",
    ),
    "P-ANALYSIS": (
        "锁定输入层、算法版本、种子和预期fixture",
        "实现确定性处理、模型或决策逻辑",
        "运行边界、缺失、敏感性和重放验证",
        "输出可复现报告、哈希、结论边界和交接数据",
    ),
    "P-INTEGRATION": (
        "冻结参与模块版本并写明端到端场景",
        "连接真实接口并完成正常纵向路径",
        "执行断流、乱序、降级、性能和无依赖故障场景",
        "归档录像、日志、构建哈希和剩余风险",
    ),
    "P-RUN": (
        "复核外部门禁、人员唯一性、manifest和构建哈希",
        "先完成设备、环境、量表和记录链演练",
        "按锁定流程执行并实时记录偏离与异常",
        "批次结束立即做QC、校验和、平衡检查与交接",
    ),
    "P-DELIVERY": (
        "列出目标受众、输入版本、交付清单和公开限制",
        "从锁定来源生成文稿、构建或归档候选",
        "执行匿名、许可、复现、主张和完整性检查",
        "由第二人复核并冻结版本、哈希和移交记录",
    ),
}


def parse_resources() -> dict[str, tuple[str, str]]:
    resources: dict[str, tuple[str, str]] = {}
    pattern = re.compile(r"^\| (L-[A-Z]+) \|.*?\| \[([^]]+)]\((https://[^)]+)\) \|")
    for line in RESOURCES.read_text(encoding="utf-8-sig").splitlines():
        match = pattern.match(line)
        if match:
            resources[match.group(1)] = (match.group(2), match.group(3))
    return resources


def list_items(value: str, separator: str = ";") -> list[str]:
    return [item.strip() for item in value.split(separator) if item.strip()]


def main() -> None:
    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    resources = parse_resources()

    lines = [
        "# SRP可领取树型任务包 v2.0",
        "",
        "> 状态：`DISPATCH_READY`",
        "> 规模：48个固定任务包 + 3个可重复批次模板。CSV登记表是状态权威；本文件由`10_render_task_handbook.py`确定性生成。",
        "",
        "## 1. 领取与验收规则",
        "",
        "1. 只领取状态为`READY`且依赖与外部门禁全部关闭的固定包；模板须先复制成唯一实例ID再领取。",
        "2. 每人同时只持有一个实现包。领取前运行`git status --short`并填写领取人、分支、复核人和时间。",
        "3. 每包依次完成四个过程阶段，不得用课程学习、Mock演示或文档存在代替验收。",
        "4. AC1至AC3全部通过、证据路径可访问、第二人复核、commit和push后才可标记`DONE`。",
        "5. 接口变化先建合同变更；领取者不得自行修改研究门、随机化、排除规则和正式阈值。",
        "6. 可重复批次模板每个实例最多12人且1至5人日；关闭任务核对全部实例，而不是把模板本身标成完成。",
        "",
        "## 2. 正向装配路径",
        "",
        "`W0基础合同 -> W1公共骨架与治理 -> W2纵向实现 -> W3集成与工具 -> W4技术预试关闭 -> W5正式阶段与锁定分析 -> W6论文投稿与成果交接`",
        "",
        "反向完整性依据见[任务拆分双向覆盖审计](09_任务拆分双向覆盖审计_v2.md)，学习资料总表见[任务技能与国内学习资料](08_任务技能与国内学习资料_v1.0.md)。",
    ]

    current_wave = None
    for row in rows:
        if row["wave"] != current_wave:
            current_wave = row["wave"]
            lines.extend(["", f"## {current_wave}任务", ""])

        refs = []
        for ref_id in row["learning_refs"].split("|"):
            title, url = resources[ref_id]
            refs.append(f"[{ref_id} {title}]({url})")
        dependencies = row["depends_on"].replace("|", "、") or "无"
        kind = "可重复模板" if row["kind"] == "TEMPLATE" else "固定任务"

        lines.extend(
            [
                f"### {row['task_id']} {row['title']}",
                "",
                f"- **归属与状态**：{row['domain']}；{kind}；`{row['status']}`；{row['effort_person_days']}人日；依赖：{dependencies}",
                f"- **所需技能**：{row['skills']}",
                f"- **学习资料**：{'；'.join(refs)}",
                f"- **交付物**：{'；'.join(list_items(row['deliverables']))}",
                "- **过程**：",
            ]
        )
        for index, step in enumerate(PROCESS_PROFILES[row["process_profile"]], start=1):
            lines.append(f"  {index}. {step}。")
        lines.append("- **验收要求**：")
        for criterion in list_items(row["acceptance_criteria"], "；"):
            lines.append(f"  - {criterion}")
        lines.extend(
            [
                f"- **证据**：{'；'.join(list_items(row['evidence_required']))}",
                f"- **完成条件**：{row['completion_condition']}",
                "",
            ]
        )

    OUTPUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"WROTE: {OUTPUT.name}; tasks={len(rows)}")


if __name__ == "__main__":
    main()
