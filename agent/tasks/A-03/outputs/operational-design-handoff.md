# A-03 操作级设计交接

验证新评分分区、参与者级模型、缺失敏感性与基于真实前置的N。

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

NORM-20261008：普通学习间隙、不诱发压力、不按NA筛选；校准前10/保留核验后10，正式冻结在前置验证之后。设计材料已交付，M01唯一中文题本/映射/指令与M02使用条件仍未关闭。本包承接参数规格：scoring_tolerance、formal_sample_size；核对定义、单位、方法、接受依据和失败收缩，真实数值不由文档冻结。

### 共同I时长容差

标识 `scoring_tolerance`；秒。独立测量误差e与有意义目标偏离m。

确定：先由专家/任务用途确定有意义偏离m，再双标注估计边界误差e；候选容差tau取可接受区间[2e,m]，保留材料验证，评分不得随G放宽。

接受：区间非空且冻结后不因组别/控制器改变；若2e>m则测量不支持该达成分类，保留连续偏差及未知界。

失败：停止合格分类，改连续描述/修测量，不宣布非劣。

### 正式样本规模

标识 `formal_sample_size`；独立参与者数。前置人员与正式样本不重计。

确定：以关注差、前后相关、残差、地板、两臂缺失范围模拟冻结ANCOVA/插补方案；给功效与95%区间精度曲线及敏感性。

接受：预定主要差和功能代价精度均可辨且资源覆盖才冻结；不足增加资源或明确估计性研究。

失败：增加资源/缩小结论，保留真实缺失而不凑样本。

