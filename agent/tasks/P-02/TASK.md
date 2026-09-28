# P-02【数据记录】L0/L1追加记录与重放

注册状态DONE，原实现Codex；傅钧烨2026-08-21见证已有验证并审阅03d7426，签署提交ea132c8。本轮执行Codex，不代填独立Agent或真人新签收。

## 范围与验收

原包约4人日。AC1：中断恢复保留旧字节，新段记录并封存，不恢复体验；AC2：篡改、删除、乱序、尾锚与封存漂移拒绝；AC3：完整提交调用重放输出一致，无设备、网络或重复暴露副作用。
P-01拥有状态和时钟，P-02只存储与重放；真实专机、授权原件、设备持续采集和完整系统不在历史DONE范围。

## 本轮步骤

1. 读取签署、归档、记录代理、重放、证据束与测试，核对原范围和实际消费者。
2. 两个生成器实际迁入execution，新结果写evidence/runtime；历史fixtures和压力记录保留原字节。
3. 运行相关回归、重建golden、执行800秒合成负载；比较封存和重放结果及计数、内存趋势。
4. 修正Agent层当前说明，从outputs/summary.json生成Word和串联审阅，登记下游缺口而不伪造完成。模块README为U12-06冻结输入，保持原字节；当前入口为outputs/current-store-contract.md。

## 上下游交接

F-01/F-05提供版本合同，P-01提供核心操作，G-02提供隐私与正式存储资格，X-01提供分配引用。D-01/D-02写原始通知包；S/I写同步与质量；A-01消费束与ReplayReader。
restricted_ref只校验声明，不读原件也不授权。A-01须获真实访问资格后核对原件。核心前教学接入后由P-01/U12-11交接实际事件，不从旧golden猜测。

## 技能与资料

Python、追加存储、fsync、锁与确定性重放。环境版本按项目基线，不新增依赖。
- [Python中文文件对象文档](https://docs.python.org/zh-cn/3/library/io.html)
- [Python中文fsync文档](https://docs.python.org/zh-cn/3/library/os.html#os.fsync)
- 国内教学和技能表见inputs中的08_任务技能与国内学习资料_v1.0.md。

inputs引用来源，execution保存工具，evidence保存本轮实际结果，outputs保存总结，archive说明历史保留。共享srp_session_store仍为原模块唯一实现，最终收拢时更新引用，不复制业务代码。
