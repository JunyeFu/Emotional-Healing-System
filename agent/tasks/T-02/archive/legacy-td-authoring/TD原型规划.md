# TouchDesigner 原型规划

> 呼吸引导圈（渲染+推送） + 实验监控台 + 实时数据曲线
> **呼吸引导圈在 TD 中渲染，通过 Spout 推送纹理到 Unity 作为背景层**

## 职责边界

```
TD 负责（渲染+监控）                           Unity 负责（沉浸体验+展示）
┌──────────────────────────────┐    ┌─────────────────────────────┐
│ · 呼吸引导圈渲染 → Spout Out   │    │ · 呼吸引导圈纹理展示（背景层）  │
│ · 实验监控台（仪表盘）          │    │ · 4种天气场景渲染              │
│ · 实时数据曲线                 │    │ · 旅人Sprite动画              │
│                              │    │ · 天气粒子特效                │
│                              │    │ · 环境提示词浮现               │
└──────────────────────────────┘    └─────────────────────────────┘
         │ Spout 纹理推送                    │ Spout Receiver 接收
         └──────────────────────────────────┘
```

TD 负责**渲染**呼吸引导圈（利用 TD 实时生成图形的优势），通过 Spout 将渲染结果作为纹理推送到 Unity。Unity 负责**展示**该纹理作为背景层，并叠加天气场景。

## 三大模块

| 模块 | 功能 | 输入 | 输出 |
|------|------|------|------|
| 呼吸引导圈 | 视觉呼吸引导（缩放/颜色）+ Spout 推送 | breath.phase + guidance.circle_radius | Spout 纹理 → Unity |
| 实验监控台 | 主试视角全局监控 | 全部 UDP JSON 字段 | 仪表盘 |
| 实时数据曲线 | 呼吸/HR/calm_index 折线图 | breath/cardiac/scores 时间序列 | CHOP 曲线 |

## 技术要点

- UDP In DAT 接收 JSON(:5005) → 解析 → 分发到各 CHOP
- 呼吸圈动画：circle_radius 驱动 Transform CHOP 缩放
- 圈颜色：吸气=暖白 #FFF8E7，屏气=淡金 #FFE4B5，呼气=冷蓝 #B5D8FF
- **Spout Out TOP**：将呼吸圈渲染结果推送到 Unity（Sender: "SRP_BreathCircle"）
- 监控台用 Panel COMP 布局，显示4维评分 + calm_index + HR + RR
- **不做**：天气背景色、天气粒子、天气强度映射 → 全部在 Unity

## Spout 推送配置

```
TD 内部信号流:
UDP:5005 → JSON解析 → CHOP数据
                        ↓
            circle_radius → Transform CHOP → Circle SOP → Render TOP
            phase → Color CHOP ↗                        ↓
                                                    Spout Out TOP
                                                   (Sender: SRP_BreathCircle)
                                                         ↓
                                                    Unity Spout Receiver
```

| 参数 | 值 |
|------|-----|
| Spout Sender 名称 | `SRP_BreathCircle` |
| 分辨率 | 1920×1080（匹配 Unity 显示分辨率） |
| 帧率 | 跟随 TD 时间线（60fps） |
| 透明度 | TD 侧渲染为半透明，Unity 叠加在背景色之上 |

## 文件结构（规划）

```
03-TouchDesigner/
├── srp_main.toe                 ← 主工程：合并呼吸引导+监控台+曲线
├── osc_bridge/                  OSC 外部控制脚本
│   ├── osc_controller.py        Python OSC 控制器 ✅
│   ├── td_osc_receiver.py       TD 内部 Execute DAT 脚本 ✅
│   ├── td_webserver_callbacks.py WebServer MCP 回调
│   ├── td_debug.py              TD 调试工具
│   └── README.md                搭建指南
├── 呼吸引导.toe                 队友交付物（待改造为 UDP 接收）
├── 呼吸引导.1.toe               队友交付物副本
├── build_srp.py                 MCP 一键构建脚本
├── udp_bridge.py                UDP 桥接测试
└── td_mcp_callbacks.py          MCP WebServer 回调
```

### 队友交付物说明

| 文件 | 内容 | 问题 | 处理 |
|------|------|------|------|
| `呼吸引导.toe` | 呼吸引导圈动画 | 使用 Serial DAT 非 UDP | 改造为 OSC In DAT + JSON Execute DAT |
| `呼吸引导.1.toe` | 同上副本 | 同上 | 同上 |

## OSC 远程遥控方案 ✅

```
外部 Python (hermes-venv)           TouchDesigner
┌────────────────────┐    OSC     ┌──────────────────────┐
│  osc_controller.py │ ──UDP:7000→│ OSC In DAT (oscin1)  │
│                    │           │ Execute DAT (exec_osc)│
│  par / exec / create│           │ td.op().par().val     │
└────────────────────┘           └──────────────────────┘
```

### 快速开始

1. **TD 内准备**: 拖入 OSC In DAT → port 7000, 拖入 Execute DAT → 加载 `td_osc_receiver.py`
2. **外部操控**: `python osc_controller.py` → 互动模式, 或 `python osc_controller.py ping` 测试
3. **一键骨架**: `python osc_controller.py srp` 自动创建 SRP 节点树

## MCP 开发桥接

> Claude Code 通过 MCP 直接操控 TD，替代手动拖拽节点。
> 详见：`02-技术研发/06-MCP开发桥接/TouchDesigner-MCP操作手册.md`

| 操作 | MCP 工具 |
|------|---------|
| 创建节点树 | `execute_python_script` (一次性创建完整骨架) |
| 查看节点参数 | `get_td_node_parameters` |
| 修改参数 | `update_td_node_parameters` |
| 调试错误 | `get_td_node_errors` |
| 环境检查 | `get_td_info` |

**架构**：Claude Code → HTTP:9980 → TD WebServer DAT → `td.op().create()` 等 API

**与 OSC 方案的关系**：MCP 搭建初始骨架 → OSC 做运行时微调（两者互补）

## Hermes Skill

| 任务 | Skill |
|------|-------|
| TD CHOP 网络设计 | 40-srp-touchdesigner-chop-network |
| UDP 接收 | 40-srp-python-osc-websocket |
