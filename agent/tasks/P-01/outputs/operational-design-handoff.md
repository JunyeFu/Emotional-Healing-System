# P-01 操作级设计交接

承接受限放慢、错相缓冲、回归及中性模式的单一决策权与预算。

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

NORM-20261008：普通学习间隙、不诱发压力、不按NA筛选；校准前10/保留核验后10，正式冻结在前置验证之后。设计材料已交付，M01唯一中文题本/映射/指令与M02使用条件仍未关闭。本包承接参数规格：rate_window、phase_offset_window、slowdown_limit、single_change_limit、stability_window、return_rate、buffer_single_limit；核对定义、单位、方法、接受依据和失败收缩，真实数值不由文档冻结。

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

### 最大放慢尺度

标识 `slowdown_limit`；无量纲alpha。共同I吸/呼统一尺度；不放大停留。

确定：由舒适反馈、实际可辨持续时间及共同目标用途形成候选尺度；前10核查，后10固定核验；不按NA组差选。

接受：所有步骤在绝对可接受时长内；停留不扩大；超界拒绝计划；目标漂移成本可独立重算。

失败：缩小上界或禁用适应，不无限迁就。

### 单周期尺度增量

标识 `single_change_limit`；alpha/周期。下一完整周期生效。

确定：用校准窗中所需尺度变化形成有限候选增量，检查突然变化感和模式摆动；保留集固定增量。

接受：不在已呈现周期内改普通G；每次变化不超候选域；产生不适或反复追逐则不接受。

失败：缩小增量或撤销放慢动作。

### 回归稳定观察窗

标识 `stability_window`；周期数。可靠X对当前G的跟随，非I达成。

确定：枚举过去完整周期窗，比较噪声扰动下进入/离开回归的反复次数及用户可解释性。

接受：不足可辨周期不回归；输入失效即时中性；抖动不导致无界反复调整。

失败：延长观察或撤下个体化。

### 回归尺度减量

标识 `return_rate`；alpha/周期。alpha_next=max(0,alpha-current_delta)。

确定：对冻结稳定窗枚举递减量，重建回归所需周期、再次偏慢和结束仍偏移比例。

接受：不得快于I；不以稳定跟上慢G声称达到I；预算内不能回归时诚实记录，不加时。

失败：减小递减量或收缩支持主张。

### 一次自然缓冲上限

标识 `buffer_single_limit`；秒。无强制停留，自然呼吸占T。

确定：用实际可辨相位时点及延迟分布推导重对齐机会，预试询问等待负担并记录用时。

接受：缓冲上限内不存在可靠开周期机会则中性；不得把缓冲画成保持/屏息；不能保证完整下一周期时收尾。

失败：取消重对齐，转中性/收尾。

