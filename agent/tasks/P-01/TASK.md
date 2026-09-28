# P-01【Python核心】manifest与会话编排

注册状态DONE。原实现Codex，真实第二人傅钧烨2026-08-21见证既有验证并审阅03d7426，签署ea132c8。本轮执行Codex，不新增真人签名。

## 验收与工作量

原任务约6人日。AC1：确定性时钟、24顺序、双提示、时长边界与暂停恢复；AC2：重复请求不推进、控制重试保持ID和序号；AC3：非法转换与正式门失败关闭、四模块默认800秒回放。核心不导入Unity或TD，传输消费F-01/F-05合同。

## 本轮过程

1. 对照注册表、已签署原件、当前核心及P-02消费者，区分历史范围和当前研究时序。
2. golden生成器实际迁入execution，新结果只写evidence/runtime；测试改用新位置，无旧入口转发。
3. 运行P-01/P-02、协议和治理测试，重建golden并比较19控制、19ACK、12回执、54事件、4决策及800秒。
4. 修正当前README，再生成outputs/summary.json对应Word及项目串联审阅，核对下游包冻结输入。

## 上下游与责任

上游F-01/F-05合同、G-02隐私与暴露门，P-02追加存储，X-01分配。下游U-01渲染镜像、T-02操作请求、I-01真实全链、U12-06正式入口。共享实现仍在02-技术研发/srp_session_core，最终整体迁移时修复消费者，不复制代码。

核心前教学由P-01与U12-11在研究冻结后接入。当前只在核心start登记暴露；不能提前展示条件教学、再用核心回归证明教学退出去重已完成。此未交付项不改写历史DONE。

## 技能与资料

必需Python、单调时钟、状态机、pytest及asyncio TCP/UDP。工具版本按项目环境读取，不在本包覆盖环境基线。
- [Python中文asyncio文档](https://docs.python.org/zh-cn/3/library/asyncio.html)
- [Python中文单调时钟文档](https://docs.python.org/zh-cn/3/library/time.html#time.monotonic_ns)
- 国内学习资源和任务技能映射见inputs中的08_任务技能与国内学习资料_v1.0.md。

固定结构：inputs来源、execution执行、evidence真实本轮结果、outputs总结、archive历史保留说明。运行verify.ps1或verify.py；Word不作为运行权威。
