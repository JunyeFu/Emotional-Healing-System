"""Generate project-owned figures for the three SRP PDF briefs."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT = font_manager.FontProperties(fname=str(FONT_PATH)) if FONT_PATH.exists() else None

COLORS = {
    "ink": "#1F2937",
    "blue": "#2F6690",
    "green": "#3A7D44",
    "gold": "#B7791F",
    "red": "#A63D40",
    "gray": "#E5E7EB",
    "light_blue": "#E8F1F8",
    "light_green": "#EAF4EA",
    "light_gold": "#F8F0DF",
}


def label(ax, x, y, text, size=9, weight="normal", color=None, ha="center", va="center"):
    ax.text(
        x,
        y,
        text,
        fontsize=size,
        fontproperties=FONT,
        fontweight=weight,
        color=color or COLORS["ink"],
        ha=ha,
        va=va,
    )


def box(ax, x, y, w, h, text, face, edge, size=9):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=1.2,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(patch)
    label(ax, x + w / 2, y + h / 2, text, size=size, weight="bold")


def arrow(ax, start, end, color=None):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.2,
            color=color or COLORS["ink"],
        )
    )


def save(fig, name):
    fig.savefig(ASSETS / name, dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def system_architecture():
    fig, ax = plt.subplots(figsize=(10.2, 4.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")

    box(ax, 0.2, 2.0, 1.45, 1.0, "真实设备采集\nPolar + PLUX", COLORS["light_gold"], COLORS["gold"])
    box(ax, 2.05, 1.75, 1.75, 1.5, "Python 会话核心\n时钟·条件·顺序\n状态·落盘", COLORS["light_blue"], COLORS["blue"])
    box(ax, 4.25, 3.05, 1.75, 1.0, "在线交互状态估计\n事件·质量·PF", COLORS["light_green"], COLORS["green"])
    box(ax, 4.25, 1.55, 1.75, 1.0, "运行合同与记录\n控制·ACK·遥测", COLORS["light_blue"], COLORS["blue"])
    box(ax, 6.55, 3.25, 1.55, 0.95, "Unity\n完整参与者体验", COLORS["light_green"], COLORS["green"])
    box(ax, 6.55, 1.85, 1.55, 0.95, "TouchDesigner\n只读操作台", COLORS["light_gold"], COLORS["gold"])
    box(ax, 6.55, 0.45, 1.55, 0.95, "离线重建\nL0 到 L5", "#F3E8EE", COLORS["red"])
    box(ax, 8.55, 1.65, 1.25, 1.35, "论文与成果\n图表·复现\n交接", COLORS["gray"], COLORS["ink"])

    arrow(ax, (1.65, 2.5), (2.05, 2.5))
    arrow(ax, (3.8, 2.75), (4.25, 3.55))
    arrow(ax, (3.8, 2.25), (4.25, 2.05))
    arrow(ax, (6.0, 2.2), (6.55, 3.7))
    arrow(ax, (6.0, 2.05), (6.55, 2.3))
    arrow(ax, (6.0, 1.85), (6.55, 0.9))
    arrow(ax, (8.1, 0.95), (8.55, 2.0))
    arrow(ax, (8.1, 3.7), (8.55, 2.65))
    label(ax, 4.95, 4.55, "Python 是运行状态唯一权威；Unity 不依赖 TD", size=10, weight="bold", color=COLORS["blue"])
    save(fig, "system_architecture.png")


def task_waves():
    fig, ax = plt.subplots(figsize=(10.4, 4.3))
    ax.set_xlim(0, 10.4)
    ax.set_ylim(0, 4.3)
    ax.axis("off")
    waves = [
        ("W0", "基础合同", "4"),
        ("W1", "骨架与前期设计", "12"),
        ("W2", "灰盒与纵向实现", "16"),
        ("W3", "集成与工具", "8"),
        ("W4", "预试关闭", "4+1T"),
        ("W5", "正式阶段", "6+2T"),
        ("W6", "论文与交接", "3"),
    ]
    palette = [COLORS["blue"], COLORS["green"], COLORS["gold"], COLORS["red"]]
    for index, (wave, title, count) in enumerate(waves):
        x = 0.15 + index * 1.47
        edge = palette[index % len(palette)]
        box(ax, x, 1.65, 1.22, 1.05, f"{wave}\n{title}\n{count}项", "white", edge, size=8.5)
        if index < len(waves) - 1:
            arrow(ax, (x + 1.22, 2.18), (x + 1.45, 2.18), edge)
    box(ax, 2.05, 0.28, 6.3, 0.72, "领取门：依赖完成 + 外部门禁关闭 + AC1-AC3 + 证据 + 第二人复核", COLORS["gray"], COLORS["ink"], size=9)
    label(ax, 5.2, 3.55, "53 个固定任务包 + 3 个可重复批次模板；Unity 新增 5 个前期设计门", size=10.5, weight="bold", color=COLORS["ink"])
    save(fig, "task_waves.png")


def experiment_flow():
    fig, ax = plt.subplots(figsize=(10.2, 5.2))
    ax.set_xlim(0, 10.2)
    ax.set_ylim(0, 5.2)
    ax.axis("off")

    box(ax, 0.3, 3.05, 2.3, 1.25, "阶段一\n场景原生 vs 抽象双环\n24 顺序均衡随机", COLORS["light_blue"], COLORS["blue"], size=9)
    box(ax, 3.95, 3.05, 2.3, 1.25, "阶段二\n参与者分组 OPE / ESS\n支持不足则均匀回退", COLORS["light_gold"], COLORS["gold"], size=9)
    box(ax, 7.6, 3.05, 2.3, 1.25, "阶段三\n同一 Unity 构建\n冻结策略 vs 均衡随机", COLORS["light_green"], COLORS["green"], size=9)
    arrow(ax, (2.6, 3.68), (3.95, 3.68))
    arrow(ax, (6.25, 3.68), (7.6, 3.68))

    box(ax, 0.35, 0.75, 1.35, 0.8, "训练后\nPANAS 前测", "white", COLORS["blue"], size=8.5)
    box(ax, 2.0, 0.75, 1.35, 0.8, "模块 1\n25+150+25 s", "white", COLORS["green"], size=8.5)
    box(ax, 3.65, 0.75, 1.35, 0.8, "模块 2\n25+150+25 s", "white", COLORS["green"], size=8.5)
    box(ax, 5.3, 0.75, 1.35, 0.8, "模块 3\n25+150+25 s", "white", COLORS["green"], size=8.5)
    box(ax, 6.95, 0.75, 1.35, 0.8, "模块 4\n25+150+25 s", "white", COLORS["green"], size=8.5)
    box(ax, 8.6, 0.75, 1.25, 0.8, "PANAS 后测\n再体验问卷", "white", COLORS["blue"], size=8.2)
    for x in (1.7, 3.35, 5.0, 6.65, 8.3):
        arrow(ax, (x, 1.15), (x + 0.3, 1.15))
    label(ax, 5.1, 2.15, "参与者核心体验内平坐观看，不进行手部操作；模块顺序由阶段规则确定", size=9.5, weight="bold")
    save(fig, "experiment_flow.png")


def main():
    system_architecture()
    task_waves()
    experiment_flow()
    print(f"WROTE: {ASSETS}")


if __name__ == "__main__":
    main()
