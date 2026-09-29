# U12-06 当前影响

五份旧原文实际归档；旧适配包及内容核验改当前导航。当前注册表的傅钧烨/IN_PROGRESS保持，没有实现候选、独立复核或真人新签署。本轮不修改P-01、P-02、随机化和Unity的业务实现，不覆盖成员正在进行的工作。

旧task_input是领取包冻结来源，明确登记原路径到archive/candidate/inputs/task_input.json；运行验证器仍核对原字节，不刷新正在进行的副本、manifest、候选与input_snapshot_id。冻结consumers继续按U12-01原文映射核对。

本轮运行观测只复用现有合成fixture：默认依赖拒绝formal、标记formal_capable的fixture可到PREPARED。它说明研究v1.2接线不能由旧测试绿灯推定，未将fixture成功登记成正式放行，也未连接设备或网络。

首轮一项当前来源检查失败，本轮误写了并不存在的P-01/current-contract.md；订正为实际P-01结构化总结，原失败日志保留initial-handoff.txt，未放宽文件存在断言。

第二轮一项旧核验入口相对链接少一层，已修正到仓库根；失败日志保留initial-navigation.txt。两轮均245项通过、一项本轮导航检查失败，不是成员业务实现失败。

第三轮首次验证时汇总尚未生成，核验入口提前链接verification.json导致循环；改为已有证据目录，失败日志保留initial-evidence-link.txt。没有创建虚假的成功报告绕过检查。

专项通过后分发验证要求迁移原件受Git跟踪；先暂存精确迁移的task_input后继续验证，既有跟踪要求未放宽，失败日志保留initial-dispatch.txt。
