# U12-04 操作级设计交接

承接NA前测校正、I/G/成本分报、完整不确定周期界和新精度候选。

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

NORM-20261008：普通学习间隙、不诱发压力、不按NA筛选；校准前10/保留核验后10，正式冻结在前置验证之后。设计材料已交付，M01唯一中文题本/映射/指令与M02使用条件仍未关闭。本包承接参数规格：scoring_tolerance、measurement_version、minimum_interesting_difference、formal_sample_size；核对定义、单位、方法、接受依据和失败收缩，真实数值不由文档冻结。

### 共同I时长容差

标识 `scoring_tolerance`；秒。独立测量误差e与有意义目标偏离m。

确定：先由专家/任务用途确定有意义偏离m，再双标注估计边界误差e；候选容差tau取可接受区间[2e,m]，保留材料验证，评分不得随G放宽。

接受：区间非空且冻结后不因组别/控制器改变；若2e>m则测量不支持该达成分类，保留连续偏差及未知界。

失败：停止合格分类，改连续描述/修测量，不宣布非劣。

### 主要测量唯一版本

标识 `measurement_version`；版本/题项/指令。中文20题PANAS候选与18题修订/PANAS-X分开。

确定：获取具体20题译本、原文及可适用使用条件，逐项核对NA映射与当前状态指令；保存来源并在认知阶段核查理解。

接受：题本、映射、计分、状态指令、使用条件全部确认才可使用；本轮未取得唯一题本，保持未关闭。

失败：不自译、不拼接、不自动换终点；禁止对应正式测量。

### 最小实际关注差

标识 `minimum_interesting_difference`；NA原始分。采用用途和可接受收益，非预期效应。

确定：在不看组间结果前，用独立用户/专家解释量表锚定变化及准备成本；不能形成共同意义则给一段决策区间并做精度敏感性。

接受：关注差必须有具体版本与产品用途依据；不能由资源100人或预试显著差倒推。

失败：定位为估计性研究，收缩确认性采用主张。

### 正式样本规模

标识 `formal_sample_size`；独立参与者数。前置人员与正式样本不重计。

确定：以关注差、前后相关、残差、地板、两臂缺失范围模拟冻结ANCOVA/插补方案；给功效与95%区间精度曲线及敏感性。

接受：预定主要差和功能代价精度均可辨且资源覆盖才冻结；不足增加资源或明确估计性研究。

失败：增加资源/缩小结论，保留真实缺失而不凑样本。

