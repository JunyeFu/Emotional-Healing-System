"""Render current task summaries and the compact status SVG from the registry."""
import csv
import html
import json
import re
import runpy
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0"
GOV = PLAN / "24_团队任务与项目治理"
GUIDE = (GOV / "u12_upgrade/README.md").relative_to(ROOT).as_posix()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main():
    with (GOV / "05_可领取任务包.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    state = next(r["status"] for r in rows if r["task_id"] == "U12-01")
    counts = Counter(r["status"] for r in rows)
    ready = "/".join(r["task_id"] for r in rows if r["status"] == "READY")
    active = "/".join(r["task_id"] for r in rows if r["status"] == "IN_PROGRESS") or "无"
    review = "/".join(r["task_id"] for r in rows if r["status"] == "IN_REVIEW") or "无"
    summary = f"治理v1.2：71项任务（68固定+3模板）；DONE={counts['DONE']}项（含18项原签收）；IN_PROGRESS={active}；IN_REVIEW={review}；A-03-SPEC为DONE；READY={ready}；真实准入与研究数值仍未冻结"
    for name, pattern, prefix in (("README.md", r"^> SRP .*?$", "> SRP · 4人团队 · "),
                                  ("AGENTS.md", r"^> (?:2026/5/20 |当前阶段：).*?$", "> 当前阶段：")):
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        text = re.sub(pattern, lambda _: prefix + summary, text, flags=re.MULTILINE)
        if name == "README.md":
            text = text.replace("单篇IJHCI目标稿以完整提示表示方案及设计知识为主贡献。", "单篇IJHCI目标稿比较场景原生与抽象控件式呼吸提示的情绪收益、代价与设计边界，不预设原生获胜。")
            text = text.replace("| 当前研究参数 | [protocol_authority_v1.1.json]", "| 当前研究候选参数 | [protocol_authority_v1.2.json]")
            text = text.replace("/00_总控/protocol_authority_v1.1.json)", "/00_总控/protocol_authority_v1.2.json)")
            text = re.sub(r"^\| 贡献、主张与证据门 .*?$", f"| 贡献、主张与证据门 | [v1.2治理入口]({GUIDE}) |", text, flags=re.MULTILINE)
        else:
            text = re.sub(r"^\| 看当前执行权威 .*?$", f"| 看当前执行权威 | `{GUIDE}` + `active_governance.json`（治理目录） |", text, flags=re.MULTILINE)
        write(path, text)
    board = "# 当前阶段看板\n\n> 2026-09-08 | " + summary + "\n\n"
    board += f"当前设计与责任入口：[U12-01](/D:/Agent/03-SRP/{GUIDE})。\n\n"
    board += "## 研究与工程分开\n\n阶段一独立支撑核心论文；阶段二/三为条件式扩展。PANAS主要比较候选与PF功能护栏分开，SCCI只作操纵检查。原新颖性REVISE_REQUIRED和研究证据缺口不因工程迁移自动解除。\n\n"
    board += "原18项签收保留原范围；新TD界面与工程壳仍需实机证据。A-03新统计规格由U12-04提供，REAL/CAL不得沿用旧规格冒充新校准。\n\n"
    board += "## 当前任务\n\n| 状态 | 任务 |\n|---|---|\n"
    for status in ("DONE", "READY", "IN_PROGRESS", "IN_REVIEW"):
        board += f"| {status} | {'、'.join(r['task_id'] for r in rows if r['status'] == status) or '无'} |\n"
    board += "\n## 下一硬门\n\nU12-01已由傅钧烨签收；当前READY任务可自主领取。U12-02/03/04/06交付汇入U12-09一致性复核，U12-07准备结果中立写作模板。U12-05仍等待外部条件。G-05真实资格、U12-11数值冻结、U12-06运行接线继续阻断正式研究。\n"
    write(ROOT / "00-项目管理/看板与进度/当前阶段看板.md", board)
    tree = "# 四人团队职责与任务树\n\n> " + summary + "\n\n"
    tree += "固定任务自主领取，领域归属明确；每个交付均需输入、分阶段过程、验收与证据。单一集成人负责注册表、协议和共享Unity资源，不按固定人员整块承包模块。\n\n"
    tree += "## 四个协作方向\n\n- 工程治理与Python：合同、时钟、记录、治理版本与可靠运行。\n- Unity与视听设计：固定场景、完整提示方案、公平教学、灰盒和风险切片。\n- 设备与TD：真实数据采集、质量、只读监控、受控请求与真实联调。\n- 测量统计与论文：前后量表、过程分析、独立功能护栏、盲态校准和结果中立报告。\n\n"
    tree += "## 正向装配\n\nU12-01 → U12-02/03/04/05/06/07 → U12-09 → 真实预试与A-03-CAL → U12-11 → G-03 → 阶段一 → A-05 → U12-10 → A-06 → W-02/W-03 → U12-12 → W-04。\n\n实际开展扩展时，A-04和U12-08额外进入A-06范围关闭；没有开展时不伪标这些任务DONE。\n\n"
    tree += "Unity主线保持 V-05 → U-03风险切片 → U-04至U-07扩展 → U-08 → I-01；设备和真实许可按各自依赖汇入。\n\n"
    tree += "[领取手册](04_可领取树型任务包_v2.0.md) | [独立任务包](当前解锁独立任务包/README.md) | [v1.2研究治理](u12_upgrade/README.md)\n"
    write(GOV / "00_四人团队职责与任务树.md", tree)
    brief = ('---\ntitle: "SRP 固定任务概要"\nauthor: "SRP 项目组"\ndate: "2026 年 9 月 8 日"\nlang: zh-CN\n---\n\n'
             '\\begin{center}\n\\textbf{摘\\quad 要}\n\\end{center}\n\n' + summary + '。阶段一核心论文独立关闭，阶段三按真实活动记录形成条件式扩展。\n\n'
             '\\textbf{关键词：} 任务分解；版本治理；交互状态估计；证据链\n\n'
             '# 任务分解问题\n\n研究目标是比较两种完整提示方案的情绪收益、代价与设计边界。任务图含71条任务与3个独立里程碑节点；68项固定任务、3项批次模板。历史DONE只覆盖原验收范围。\n\n'
             '# 波次与装配路径\n\n| 波次 | 固定 | 模板 |\n|---|---:|---:|\n')
    for wave in (f"W{i}" for i in range(7)):
        part = [r for r in rows if r["wave"] == wave]
        brief += f"| {wave} | {sum(r['kind']=='FIXED' for r in part)} | {sum(r['kind']=='TEMPLATE' for r in part)} |\n"
    brief += "\n# 固定任务的统一过程与验收\n\n核对冻结输入，按领域实施，执行正例与负例或取得真实回执，提交独立复核与真实第二人签收。只有READY任务可领取；每个分发包包含TASK、FILES、manifest与输入快照。\n\n"
    brief += f"A-03-SPEC保持原签收；U12-04为新规格，A-03-REAL消费后进入CAL。U12-11必须消费盲态校准版本，再冻结N与界值。U12-01当前为{state}，签收范围见真实第二人报告。\n\n"
    brief += "# 完整任务目录\n\n\\small\n\n| 编号 | 领域与任务 | 状态 |\n|---|---|---|\n"
    for r in rows:
        brief += f"| {r['task_id']} | {r['title']} | {r['status']} |\n"
    brief += "\n\\normalsize\n\n# 核心收尾与条件式扩展\n\nA-05、U12-10和A-06构成核心证据关闭；W-02消费A-06与结果中立稿。开展阶段三时附A-04、U12-08与真实台账，不允许用人工布尔值隐去已开展活动。W-04最后消费U12-12。\n\n"
    brief += "# 当前限制与下一步\n\n正式采集尚未放行；新研究数值、教学时序、量表许可与机构资格仍需冻结。运行v1.2接线归U12-06，旧程序不会因设计JSON而自动获得新门。Unity和TD新画面、真实设备与LIVE_E2E证据不能由本次治理测试替代。\n"
    write(ROOT / "04-成果与交付/PDF简报/02_固定任务概要.md", brief)
    # Compact status companion to the full dependency graph, with stable row heights.
    width, row_h = 1800, 62
    height = 260 + len(rows) * row_h
    esc = html.escape
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="#fafafa"/>',
           '<g font-family="Microsoft YaHei, sans-serif" fill="#202124">',
           '<text x="50" y="60" font-size="32" font-weight="bold">SRP 任务状态与研究准入</text>',
           f'<text x="50" y="105" font-size="20">71任务 / 68固定 / 3模板 · U12-01 {state} · READY {ready}</text>',
           f'<text x="50" y="143" font-size="18">DONE {counts["DONE"]}项（含18项原签收）；未冻结数值、真实资格和运行接线不自动放行。</text>',
           '<text x="50" y="184" font-size="18">任务与领域</text><text x="1080" y="184" font-size="18">状态</text><text x="1340" y="184" font-size="18">前置依赖</text>']
    for i, r in enumerate(rows):
        y = 205 + i * row_h
        fill = '#edf5ed' if r['status'] == 'DONE' else '#eef2f8' if r['status'] == 'READY' else '#ffffff'
        out.append(f'<rect x="35" y="{y}" width="1730" height="{row_h-3}" fill="{fill}"/>')
        for x, value, size in ((50, r['task_id'] + ' ' + r['title'], 20), (1080, r['status'], 18), (1340, r['depends_on'] or '-', 13)):
            out.append(f'<text x="{x}" y="{y+36}" font-size="{size}">{esc(value)}</text>')
    out.append('</g></svg>')
    destination = ROOT / "04-成果与交付/项目流程图"
    write(destination / "SRP_任务状态与门禁解释清单_v1.0.svg", '\n'.join(out))
    runpy.run_path(str(ROOT / "Tools/Governance/render_team_task_flow.py"))["main"]()
    write(destination / "SRP_项目任务关联与门禁流程_v1.0.svg", (ROOT / "00-项目管理/看板与进度/SRP团队任务分工与门禁_当前状态.svg").read_text(encoding="utf-8"))
    print("WROTE: governance entrypoints, board, tree, brief and SVG pair")


if __name__ == "__main__":
    main()
