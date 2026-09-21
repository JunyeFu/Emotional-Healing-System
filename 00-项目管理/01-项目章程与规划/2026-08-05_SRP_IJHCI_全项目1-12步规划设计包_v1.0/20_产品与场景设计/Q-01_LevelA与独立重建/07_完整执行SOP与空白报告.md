# Q-01 完整执行SOP与空白报告 v1.0

> 当前状态：工具已填充，真人活动未执行。活动必须由E-01在U12-05及相应资格成立后实施。

## 1. 执行前冻结

1. 记录材料版本、活动资格和负责人；
2. 确认8名专家、4名设计者、2名评分者角色互斥且均非框架作者；
3. 在仓库外保存身份映射；仓库内只使用代码；
4. 用`tools/validate_q01_materials.py`验证材料；
5. 先做一次不计入正式结果的流程预演，检查说明、材料顺序、显示条件和记录表；预演数据不得并入正式评分。

## 2. 专家审查

向8名专家分别发放`01_构念专家审查包.md`、`04_课题实际构念与证据矩阵.md`和个人评分表。独立回收后运行汇总工具；若任一I-CVI、S-CVI/Ave或关键阻断不满足合同，先修订再决定是否开启独立重建。

## 3. 独立重建

向4名设计者只发放`05_盲态材料母版与编号方案.md`中的盲态部分和个人编号。统一画布比例、提交时限、可用软件与答疑口径；不得展示现有场景。D01/D03与D02/D04使用相反顺序。

## 4. 盲态评分

负责人移除文件元数据和身份线索，随机排列8个“设计者×任务”输出。两名评分者在同一显示分辨率与观看条件下先完整查看一遍，再独立依据`03_盲态评分手册.md`与`06_重建真值与评分键.md`评分。全部完成前不返回修改早先记录。

## 5. 裁定与交接

运行：

```powershell
py -3.14 tools/summarize_q01.py --roster templates/roster.csv --expert templates/expert_reviews.csv --reconstruction templates/reconstruction_scores.csv --out q01_summary.json
```

按工具输出形成`PASS`、`REVISE`、`DOWNGRADE_TO_FOUR_SCENE_DESIGN_PATTERN`或`INCOMPLETE`。任何修订写入`templates/revision_log.csv`并升级版本；原始独立记录不覆盖。

## 6. 空白执行报告

| 项 | 回填 |
|---|---|
| 活动资格与日期 | 待E-01真实执行 |
| 材料版本 | v1.0 |
| 专家角色构成 | 待回填 |
| 设计者角色构成 | 待回填 |
| 评分者构成 | 待回填 |
| I-CVI范围 | 待计算 |
| S-CVI/Ave | 待计算 |
| 关键阻断项 | 待汇总 |
| 双任务通过人数 | 待计算 |
| 评分分歧 | 待裁定 |
| 最终裁定 | `INCOMPLETE`，直至真实记录齐全 |
| 适用边界 | 仅所测材料、人员与任务；不得外推为最终体验结果 |

## 7. 方法参考

- [COSMIN Content Validity Manual](https://www.cosmin.nl/wp-content/uploads/COSMIN-manual-V2_final.pdf)：相关性、完整性、可理解性分开，独立评审后再汇总。
- [ITU-T P.910](https://www.itu.int/rec/t-rec-p.910)：预演按正式流程运行、固定呈现条件、预演评分不进入正式结果。
- [Munzner Nested Model](https://www.cs.ubc.ca/labs/imager/tr/2009/NestedModel/)：按问题、抽象、编码与实现层分别识别威胁。
- [Design Study Methodology](https://ieeexplore.ieee.org/document/6327248/)：从真实问题分析、设计、验证到反思形成可迁移知识。
