# 四种情绪天气设计

> 情绪→天气隐喻 → 呼吸策略 → 恢复信号 → 视觉要素

## 天气矩阵

| 天气 | 情绪 | 隐喻 | 呼吸策略 | 恢复信号 | 色调 | 粒子 |
|------|------|------|----------|----------|------|------|
| 风暴 🌩️ | 焦虑 | 混乱、失控 | 4-2-6 盒式呼吸 | 保护罩修复、风雨减弱 | 暗灰+紫电 | 雨滴、闪电、碎片 |
| 炙烤 🔥 | 烦躁 | 闷热、急躁 | 长呼气降温(1:2) | 热浪消退、冷色气流 | 橙红+白热 | 热浪波纹、火星 |
| 暴雪 ❄️ | 低落 | 冻结、停滞 | 稳定呼吸+微行动 | 脚印显现、雪势减弱 | 灰白+冰蓝 | 雪花、冰晶、雾气 |
| 褪色 🌫️ | 孤独 | 连接感下降 | 自主呼吸+感官连接 | 世界重新上色 | 灰白→彩色 | 色彩粒子、光点 |

## 设计约束

- 每种天气只做**1个核心视觉机制**，不扩展多场景
- 旅人始终可见（作为用户投射对象）
- 提示词从环境自然出现（雨幕裂开、热浪中浮现文字），不用对话框
- 恢复过程渐进式：重→中→轻→转晴（3-5分钟）

## 参考文献（04-gamification-emotion/）

- `Art and Psychological Well-Being Linking the Brain to the Aesthetic Emotion.pdf`
- `Form and color visual perception in green exercise Positive effects on.pdf`
- `A biophilic mind-set for a restorative built environment.pdf`

## Hermes Skill

| 任务 | Skill |
|------|-------|
| 天气视觉概念设计 | 视觉设计阶段需加载 40-srp-2d-pixel-visual-design（2D横板像素化风格） |
| TouchDesigner 实现 | 40-srp-touchdesigner-chop-network |
| Unity 2D 视觉实现 | 40-srp-unity-osc-runtime, 40-srp-animation-state-machine |
| 用户测试验证 | 40-srp-experiment-design |
