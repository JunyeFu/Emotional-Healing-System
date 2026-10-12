# S-01 操作级设计交接

区分连接、原始质量、新鲜度及关键步骤可辨性。

设计候选ODES-20261008；本轮三项设计已交付，原业务状态、历史签收及领取输入保持。真实执行/复核仍按TASK验收，不继承历史通过。

- [05-control-spec.tex](../../../design/design-foundation-20261008/05-control-spec.tex)
- [05-control-spec.pdf](../../../design/design-foundation-20261008/05-control-spec.pdf)
- [06-paired-storyboards.tex](../../../design/design-foundation-20261008/06-paired-storyboards.tex)
- [06-paired-storyboards.pdf](../../../design/design-foundation-20261008/06-paired-storyboards.pdf)
- [07-protocol-candidate.tex](../../../design/design-foundation-20261008/07-protocol-candidate.tex)
- [07-protocol-candidate.pdf](../../../design/design-foundation-20261008/07-protocol-candidate.pdf)
- [operational-design.json](../../../design/design-foundation-20261008/operational-design.json)

普通调整仅在周期边界；中断可即时撤下要求。X不能由G或画面补造；I达成、G跟随与调整成本分报。数值参数、可辨性、量表版本、关注差及N待真实校准/冻结。

## 规范化材料与确定方法

NORM-20261008：普通学习间隙、不诱发压力、不按NA筛选；校准前10/保留核验后10，正式冻结在前置验证之后。设计材料已交付，M01唯一中文题本/映射/指令与M02使用条件仍未关闭。本包承接参数规格：signal_quality、freshness；核对定义、单位、方法、接受依据和失败收缩，真实数值不由文档冻结。

### 质量可用判定

标识 `signal_quality`；状态/概率。独立双标注的原始波形和运动片段；可用不等于所有步骤可辨。

确定：校准集包含静止、运动、松动和断流；双人盲标可用与不可用，第三人裁决。候选阈值按误用时段及错误事件代价选，保留集报告参与者级误判/漏判区间。

接受：仅在误用造成的边界误差与U/T不确定宽满足先验评分域时保留；任何断流不得产生实际成功或新增累计。

失败：保持中性；改传感器/算法后用新核验材料重验。

### 数据新鲜度

标识 `freshness`；毫秒。采集时间、接收时间、真实呈现时间；仅使用决策前已到达信息。

确定：记录跨设备时钟误差和端到端延迟分布，校准允许数据龄。保留集注入迟到/乱序/中断，重建每次决定当时可见输入。

接受：数据龄上界加时钟/呈现不确定度须小于最短可辨步骤及合法边界裕量；过期不得触发个体化。

失败：撤下X响应并中性；重新同步。

