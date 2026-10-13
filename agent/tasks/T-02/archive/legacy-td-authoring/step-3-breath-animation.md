# Step 3: 引导圈动画驱动 + 监控台面板布局

## 当前状态

`呼吸引导.toe` (port 9980)，`/project1/SRP_BreathGuide/` 节点树完整，UDP 数据流已验证通过：
- `udp_in` (UDP In DAT:5005) 接收 JSON → `json_parser` (onReceive) → Data_CHOPs 14 个 CHOP 更新 ✅
- Monitor_Panel 12 个 Text TOP 文本实时刷新 ✅
- **但引导圈不会动** — circle_xform.sx/sy 未被 ch_circle_radius 驱动
- **phase_tint 颜色不变** — 未被 ch_phase_num 驱动
- **监控台无布局** — Text TOP 散落，无 Panel COMP 组织

## 目标

完成 TD 端 MVP 全部视觉功能：

### A. 引导圈动画（计划 3.3 节）

在 `onReceive` 回调中增加驱动逻辑：

| 相位 | phase_num | circle_xform.sx/sy | phase_tint 颜色 |
|------|:--:|------|------|
| inhale | 0 | 0.3 → 0.8 (@ 4s) | 绿色 (0.1, 0.8, 0.2) |
| hold | 1 | 0.8 保持 | 黄色 (0.9, 0.8, 0.1) |
| exhale | 2 | 0.8 → 0.3 (@ 6s) | 蓝色 (0.1, 0.3, 0.8) |

实现方式：`ch_circle_radius` 值由 Python mock 端计算好（已包含 0.3~0.8 的正弦变化），直接在 onReceive 中读取并设置 `circle_xform.par.sx/sy`。相位颜色同样读取 `ch_phase_num` 并设置 `phase_tint.fillcolorr/g/b`。

### B. 监控台面板布局

将 Monitor_Panel 容器内的 Text TOP 用 Panel COMP 组织成易读的主试监控界面：
- 左侧：8 维评分纵向排列
- 右上：天气汇总 + HR 信息
- 底部：提示词文本

用 Panel COMP 的 tab 布局参数控制位置。

### C. 端到端验证

启动 `main.py --weather storm --duration 30`，在 TD 中：
1. 切换到 Out TOP 视图
2. 观察引导圈随呼吸缩放 + 颜色切换
3. 观察监控台文本刷新

## 执行操作

### 操作 1: 更新 `onReceive` 回调脚本（增加动画驱动）

通过 HTTP POST 到 `/api` 的 `execute` action，更新 `json_parser` 的 `onReceive` 函数，在现有 CHOP 更新逻辑末尾增加：

```python
# --- 引导圈动画驱动 ---
bg = op('/project1/SRP_BreathGuide/Breath_Guide')
xform = bg.op('circle_xform')
tint = bg.op('phase_tint')

# 半径驱动
radius = float(breath.get('circle_radius', 0.3))
if xform:
    xform.par.sx = radius
    xform.par.sy = radius

# 相位颜色驱动
phase = str(breath.get('phase', 'inhale'))
if tint:
    if phase == 'inhale':
        tint.par.fillcolorr = 0.1
        tint.par.fillcolorg = 0.8
        tint.par.fillcolorb = 0.2
    elif phase == 'hold':
        tint.par.fillcolorr = 0.9
        tint.par.fillcolorg = 0.8
        tint.par.fillcolorb = 0.1
    else:  # exhale
        tint.par.fillcolorr = 0.1
        tint.par.fillcolorg = 0.3
        tint.par.fillcolorb = 0.8
```

### 操作 2: 监控台布局（可选，视复杂度）

尝试通过 Python API 设置 Panel COMP 参数组织 Monitor_Panel。如果 TD Python API 不支持 Panel COMP 布局参数，则跳过，由用户在 TD 界面手动拖拽排列。

## 预期结果

- 引导圈缩放随 `circle_radius` 变化（肉眼可见）
- 圈颜色随 `breath.phase` 在绿/黄/蓝之间切换
- 监控台文本持续刷新

## 验证

```bash
# 启动 data pipeline
python main.py --weather storm --duration 30

# 在 TD 中切换到 Out TOP 视图观察
# 同时检查 CHOP 值
curl -s -X POST http://127.0.0.1:9980/api \
  -H "Content-Type: application/json" \
  -d '{"action":"execute","params":{"code":"xform = op(\"/project1/SRP_BreathGuide/Breath_Guide/circle_xform\")\nprint(xform.par.sx.eval())","return_expression":"xform.par.sx.eval()"}}'
```

## 回滚

`build_srp.py` 保存了完整重建脚本。如出错，删除 `/project1/SRP_BreathGuide` 容器，重新执行 `build_srp.py` 即可。
