# SRP运行合同v2.1

本目录是F-01交付的机器可读合同。`runtime-contract-v2.1.schema.json`是线格式、必填字段、枚举和无状态跨字段约束的机器权威；`runtime_contract.py`是标准库参考实现。两者必须对同一fixture和差分负例产生相同的接受或拒绝结果。`ControlEventLedger`单独负责无法由JSON Schema表达的跨消息幂等与序号状态。

## 权威边界

- Python是会话、顺序、单调时钟、交互状态估计、降级和记录的唯一权威。
- Unity只消费可靠控制和UDP 5006遥测，并产生ACK与渲染回执。
- TouchDesigner只消费UDP 5005遥测，不得直接控制Unity或覆盖权威记录。
- TCP 5010保留给可靠控制、ACK、回执及TD请求；具体服务器与重连由P-01、U-01和T-02实现。
- 正式模式禁止Mock、未知Unity构建、缺失manifest和退休字段`calm_index`。
- Unity、TouchDesigner或其他消费者不得只复制字段名；必须用Schema生成/校验无状态消息，并实现合同测试fixture。Python特有错误码不能改变Schema的接受/拒绝边界。

## 兼容规则

1. `schema_version`不等于`2.1`时失败关闭。
2. 缺失必需字段、非法枚举、非有限数值和正式Mock失败关闭。
3. 已知退休或危险字段按显式规则拒绝。
4. 其他未知字段完成基础校验后由`validate_and_filter`丢弃，不能进入状态推进或渲染接口。
5. 重复`event_id`和非递增`control_seq`由`ControlEventLedger`拒绝，调用方不得推进状态；拒绝前分别追加`duplicate_ignored`或`rejected`审计记录。
6. JSON Schema的`integer`按数学整数解释；Python接受原生任意精度整数和有限的整数值浮点数，不把超大整数转换为浮点数。
7. `dev_mock`、`dev_replay`和`formal_*`分别绑定`mock`、`replay`和`real`来源策略；仅`dev_mock`可使用Mock设备源。
8. 阶段一策略决策的行为概率严格等于剩余候选动作数的倒数；降级标记和原因必须双向一致。

## 验证

```powershell
py -3.14 -m pip install -r "02-技术研发/05-通信协议/tests/contract/requirements.txt"
py -3.14 -m pytest "02-技术研发/05-通信协议/tests/contract" -q
pwsh -NoProfile -File "02-技术研发/05-通信协议/contracts/verify_non_python_consumer.ps1"
```

fixture哈希采用`canonical-lf-v1`：只将CRLF规范化为LF后计算SHA-256，因此Windows工作区与Git归档得到相同证据，但任何其他字节变化仍会失败。由项目根目录执行以下命令重建：

```powershell
py -3.14 "02-技术研发/05-通信协议/contracts/generate_fixture_hashes.py"
```
