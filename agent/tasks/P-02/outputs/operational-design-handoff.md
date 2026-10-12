# P-02 操作级设计交接

分别记录计划、有效下发、实际呈现、真实事件及决定时可用输入。

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

NORM-20261008：普通学习间隙、不诱发压力、不按NA筛选；校准前10/保留核验后10，正式冻结在前置验证之后。设计材料已交付，M01唯一中文题本/映射/指令与M02使用条件仍未关闭。本包承接参数规格：freshness、presentation_latency；核对定义、单位、方法、接受依据和失败收缩，真实数值不由文档冻结。

### 数据新鲜度

标识 `freshness`；毫秒。采集时间、接收时间、真实呈现时间；仅使用决策前已到达信息。

确定：记录跨设备时钟误差和端到端延迟分布，校准允许数据龄。保留集注入迟到/乱序/中断，重建每次决定当时可见输入。

接受：数据龄上界加时钟/呈现不确定度须小于最短可辨步骤及合法边界裕量；过期不得触发个体化。

失败：撤下X响应并中性；重新同步。

### 主运动实际呈现时延

标识 `presentation_latency`；毫秒。采集/决定/接收/实际呈现分别记录。

确定：使用共同时间参考与真实显示核查，分离主运动和装饰粒子；取各天气/条件尾部延迟及不确定度。

接受：时延加边界误差不得跨越待判别的关键步骤；计划或消息到达不代替实际G，回执缺失记未知。

失败：减装饰/简载体；主状态不可可靠呈现时中性。

