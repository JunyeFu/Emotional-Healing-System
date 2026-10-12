# V-01 操作级设计交接

安排共同预算、自然缓冲占时、暂停恢复及统一主要后测时点。

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

NORM-20261008：普通学习间隙、不诱发压力、不按NA筛选；校准前10/保留核验后10，正式冻结在前置验证之后。设计材料已交付，M01唯一中文题本/映射/指令与M02使用条件仍未关闭。本包承接参数规格：buffer_single_limit、buffer_total_limit；核对定义、单位、方法、接受依据和失败收缩，真实数值不由文档冻结。

### 一次自然缓冲上限

标识 `buffer_single_limit`；秒。无强制停留，自然呼吸占T。

确定：用实际可辨相位时点及延迟分布推导重对齐机会，预试询问等待负担并记录用时。

接受：缓冲上限内不存在可靠开周期机会则中性；不得把缓冲画成保持/屏息；不能保证完整下一周期时收尾。

失败：取消重对齐，转中性/收尾。

### 模块累计缓冲预算

标识 `buffer_total_limit`；秒及占T比例。不得增加暴露时间或机会。

确定：累计自然缓冲及核心练习占时；在校准材料中核查多次触发后剩余完整周期，评估用户负担。

接受：总缓冲不超过事前预算；达到界限停止调整；不以减少周期机会改I评分分母。

失败：收缩缓冲动作或改共同剂量候选。

