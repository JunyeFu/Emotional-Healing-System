# F-05 操作级设计交接

形成I/G/X步骤身份、中断语义、合法动作和R01至R10合同候选。

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

NORM-20261008：普通学习间隙、不诱发压力、不按NA筛选；校准前10/保留核验后10，正式冻结在前置验证之后。设计材料已交付，M01唯一中文题本/映射/指令与M02使用条件仍未关闭。本包承接参数规格：rate_window、phase_offset_window；核对定义、单位、方法、接受依据和失败收缩，真实数值不由文档冻结。

### 真实偏慢观察窗

标识 `rate_window`；完整周期数。决策前可辨X对已呈现G的持续时间。

确定：在相同原始X上构造相位平移而不改时长、真实拉长时长及混合扰动；从可用历史周期数枚举窗，冻结后核验。

接受：纯相位平移不得单独触发R07；真实持续偏慢的可辨动作须在剩余预算内起效，无法分辨则不调整。

失败：禁用R07；使用中性和原方案。

### 稳定错相窗与容差

标识 `phase_offset_window`；周期数/秒。存在可靠事件对应；时长相容不等于全局同相。

确定：枚举事件对应及相位稳定窗；用纯错相、慢速、抖动和无对应材料检验R08。

接受：无可靠对应不重对齐；纯慢速不误作错相；重对齐收益必须超过事件与呈现时点联合误差。

失败：取消R08，保留有限放慢与中性。

