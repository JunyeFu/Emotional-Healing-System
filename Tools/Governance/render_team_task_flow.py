"""Render the current SRP task dependency and gate map as SVG."""

from __future__ import annotations

import csv
import html
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理"
REGISTRY = GOV / "05_可领取任务包.csv"
OUTPUT = ROOT / "00-项目管理/看板与进度/SRP团队任务分工与门禁_当前状态.svg"

WAVES = [f"W{i}" for i in range(7)]
STATUS = {
    "DONE": ("#166534", "#dcfce7"),
    "READY": ("#1d4ed8", "#dbeafe"),
    "IN_PROGRESS": ("#9a3412", "#ffedd5"),
    "IN_REVIEW": ("#6b21a8", "#f3e8ff"),
    "WAIT_DEP": ("#475569", "#f1f5f9"),
    "WAIT_DEP_EXTERNAL": ("#9f1239", "#ffe4e6"),
    "BLOCKED_EXTERNAL": ("#991b1b", "#fee2e2"),
}
DOMAIN = {
    "合同与协议": "#dbeafe",
    "Python核心": "#dbeafe",
    "数据记录": "#dbeafe",
    "TouchDesigner": "#ccfbf1",
    "Unity": "#ffedd5",
    "Unity前期设计": "#fce7f3",
    "Unity预制作": "#ffedd5",
    "Unity场景": "#ffedd5",
    "研究设计": "#fce7f3",
    "体验设计": "#fce7f3",
    "研究治理": "#ede9fe",
    "数据治理": "#ede9fe",
    "设备接入": "#dcfce7",
    "信号处理": "#dcfce7",
    "交互状态估计": "#dcfce7",
    "系统集成": "#cffafe",
    "技术预试": "#cffafe",
    "正式门": "#fee2e2",
    "研究运行": "#fef3c7",
    "形成性预试": "#fef3c7",
    "统计分析": "#fef3c7",
    "分析准备": "#fef3c7",
    "正式分析": "#fef3c7",
    "策略学习": "#fef3c7",
    "预注册与锁定": "#ede9fe",
    "正式批次": "#fef3c7",
    "研究关闭": "#fef3c7",
    "最终分析": "#fef3c7",
    "论文写作": "#e2e8f0",
    "投稿复现": "#e2e8f0",
    "成果交接": "#e2e8f0",
}


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def shorten(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def main() -> None:
    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {row["task_id"]: row for row in rows}
    by_wave: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_wave[row["wave"]].append(row)

    margin_x, top = 70, 360
    col_w, col_gap = 500, 34
    node_h, row_gap = 138, 28
    width = margin_x * 2 + len(WAVES) * col_w + (len(WAVES) - 1) * col_gap
    max_rows = max(len(by_wave[wave]) for wave in WAVES)
    height = top + max_rows * (node_h + row_gap) + 420
    positions: dict[str, tuple[float, float]] = {}
    for wave_index, wave in enumerate(WAVES):
        x = margin_x + wave_index * (col_w + col_gap)
        for row_index, row in enumerate(by_wave[wave]):
            positions[row["task_id"]] = (x, top + row_index * (node_h + row_gap))

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8"/></marker>',
        '<filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.10"/></filter>',
        "</defs>",
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="70" y="68" font-family="Microsoft YaHei, sans-serif" font-size="38" font-weight="700" fill="#0f172a">SRP 团队任务分工、依赖与门禁</text>',
        '<text x="70" y="108" font-family="Microsoft YaHei, sans-serif" font-size="19" fill="#475569">状态快照 · 2026-09-01 · F-05 已由傅钧烨签署 PASS / DONE</text>',
    ]

    counts = Counter(row["status"] for row in rows)
    x = 70
    for status in ("DONE", "READY", "IN_PROGRESS", "IN_REVIEW", "WAIT_DEP", "WAIT_DEP_EXTERNAL", "BLOCKED_EXTERNAL"):
        stroke, fill = STATUS[status]
        label = f"{status} {counts.get(status, 0)}"
        box_w = 30 + len(label) * 12
        out.extend([
            f'<rect x="{x}" y="132" width="{box_w}" height="38" rx="19" fill="{fill}" stroke="{stroke}"/>',
            f'<text x="{x + box_w / 2}" y="157" text-anchor="middle" font-family="Consolas, sans-serif" font-size="15" font-weight="700" fill="{stroke}">{label}</text>',
        ])
        x += box_w + 14

    gates = [
        ("F-05 合同门", "DONE → U-01 / U-02 已解锁", "#dcfce7", "#166534"),
        ("F-04 TD 壳门", "DONE → T-01 已解锁", "#dcfce7", "#166534"),
        ("V-04 预演门", "IN_PROGRESS → V-05 继续等待", "#ffedd5", "#9a3412"),
        ("设备与外部门", "D-01 / D-02 / 后续研究链保持阻断", "#fee2e2", "#991b1b"),
    ]
    gate_y, gate_w = 196, (width - 140 - 3 * 18) / 4
    for index, (title, body, fill, stroke) in enumerate(gates):
        gx = 70 + index * (gate_w + 18)
        out.extend([
            f'<rect x="{gx}" y="{gate_y}" width="{gate_w}" height="92" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="2"/>',
            f'<text x="{gx + 18}" y="{gate_y + 32}" font-family="Microsoft YaHei, sans-serif" font-size="18" font-weight="700" fill="{stroke}">{esc(title)}</text>',
            f'<text x="{gx + 18}" y="{gate_y + 64}" font-family="Microsoft YaHei, sans-serif" font-size="15" fill="#334155">{esc(body)}</text>',
        ])

    for wave_index, wave in enumerate(WAVES):
        x0 = margin_x + wave_index * (col_w + col_gap)
        out.extend([
            f'<rect x="{x0}" y="310" width="{col_w}" height="42" rx="10" fill="#0f172a"/>',
            f'<text x="{x0 + col_w / 2}" y="338" text-anchor="middle" font-family="Microsoft YaHei, sans-serif" font-size="19" font-weight="700" fill="white">{wave} · {len(by_wave[wave])} 项</text>',
        ])

    for row in rows:
        tx, ty = positions[row["task_id"]]
        for dep in [item for item in row["depends_on"].split("|") if item in positions]:
            sx, sy = positions[dep]
            if sx == tx:
                start_x, start_y = sx + col_w / 2, sy + node_h
                end_x, end_y = tx + col_w / 2, ty
                mid_y = (start_y + end_y) / 2
                path = f"M {start_x} {start_y} C {start_x + 80} {mid_y}, {end_x + 80} {mid_y}, {end_x} {end_y}"
            else:
                start_x, start_y = sx + col_w, sy + node_h / 2
                end_x, end_y = tx, ty + node_h / 2
                bend = max(45, (end_x - start_x) * 0.42)
                path = f"M {start_x} {start_y} C {start_x + bend} {start_y}, {end_x - bend} {end_y}, {end_x} {end_y}"
            out.append(f'<path d="{path}" fill="none" stroke="#94a3b8" stroke-width="1.4" opacity="0.46" marker-end="url(#arrow)"/>')

    for row in rows:
        task_id = row["task_id"]
        x0, y0 = positions[task_id]
        stroke, status_fill = STATUS[row["status"]]
        domain_fill = DOMAIN.get(row["domain"], "#e2e8f0")
        title = row["title"].split("】", 1)[-1]
        deps = row["depends_on"].replace("|", " · ") or "起点任务"
        dash = ' stroke-dasharray="8 6"' if row["status"] in {"WAIT_DEP", "WAIT_DEP_EXTERNAL", "BLOCKED_EXTERNAL"} else ""
        out.extend([
            f'<g filter="url(#shadow)"><rect x="{x0}" y="{y0}" width="{col_w}" height="{node_h}" rx="13" fill="white" stroke="{stroke}" stroke-width="3"{dash}/>',
            f'<rect x="{x0}" y="{y0}" width="12" height="{node_h}" rx="6" fill="{domain_fill}"/>',
            f'<rect x="{x0 + 22}" y="{y0 + 16}" width="76" height="30" rx="8" fill="{domain_fill}"/>',
            f'<text x="{x0 + 60}" y="{y0 + 37}" text-anchor="middle" font-family="Consolas, sans-serif" font-size="17" font-weight="700" fill="#0f172a">{task_id}</text>',
            f'<rect x="{x0 + col_w - 174}" y="{y0 + 16}" width="156" height="30" rx="15" fill="{status_fill}" stroke="{stroke}"/>',
            f'<text x="{x0 + col_w - 96}" y="{y0 + 37}" text-anchor="middle" font-family="Consolas, sans-serif" font-size="13" font-weight="700" fill="{stroke}">{row["status"]}</text>',
            f'<text x="{x0 + 24}" y="{y0 + 75}" font-family="Microsoft YaHei, sans-serif" font-size="18" font-weight="700" fill="#0f172a">{esc(shorten(title, 24))}</text>',
            f'<text x="{x0 + 24}" y="{y0 + 103}" font-family="Microsoft YaHei, sans-serif" font-size="14" fill="#475569">类型：{esc(row["domain"])} · {row["effort_person_days"]}人日</text>',
            f'<text x="{x0 + 24}" y="{y0 + 127}" font-family="Microsoft YaHei, sans-serif" font-size="13" fill="#64748b">依赖：{esc(shorten(deps, 42))}</text></g>',
        ])

    legend_y = height - 300
    out.extend([
        f'<rect x="70" y="{legend_y}" width="{width - 140}" height="210" rx="18" fill="white" stroke="#cbd5e1"/>',
        f'<text x="94" y="{legend_y + 40}" font-family="Microsoft YaHei, sans-serif" font-size="21" font-weight="700" fill="#0f172a">读图规则</text>',
        f'<text x="94" y="{legend_y + 74}" font-family="Microsoft YaHei, sans-serif" font-size="15" fill="#334155">箭头表示任务依赖；节点底部同时列出依赖，便于在连线密集处核对。边框表示状态，左侧色条表示任务类型。</text>',
        f'<text x="94" y="{legend_y + 106}" font-family="Microsoft YaHei, sans-serif" font-size="15" fill="#334155">READY 仅表示所有仓库内前置任务已 DONE 且可领取，不表示实现、正式构建或联合运行已经完成。</text>',
        f'<text x="94" y="{legend_y + 138}" font-family="Microsoft YaHei, sans-serif" font-size="15" fill="#334155">IN_REVIEW 仍受复核或外部门约束；WAIT_DEP_EXTERNAL / BLOCKED_EXTERNAL 不可由仓库内文件自行关闭。</text>',
        f'<text x="94" y="{legend_y + 178}" font-family="Consolas, Microsoft YaHei, sans-serif" font-size="14" fill="#64748b">Source: 05_可领取任务包.csv · Renderer: Tools/Governance/render_team_task_flow.py</text>',
        "</svg>",
    ])
    OUTPUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"rendered {len(rows)} tasks to {OUTPUT}")


if __name__ == "__main__":
    main()
