# SRP运行合同v2.1

本目录是F-01交付的机器可读合同。`runtime-contract-v2.1.schema.json`供Python、Unity和TouchDesigner生成或校验各自的数据类型；`fixtures/`提供跨语言合同测试输入。

## 权威边界

- Python是会话、顺序、单调时钟、交互状态估计、降级和记录的唯一权威。
- Unity只消费可靠控制和UDP 5006遥测，并产生ACK与渲染回执。
- TouchDesigner只消费UDP 5005遥测，不得直接控制Unity或覆盖权威记录。
- TCP 5010保留给可靠控制、ACK、回执及TD请求；具体服务器与重连由P-01、U-01和T-02实现。
- 正式模式禁止Mock、未知Unity构建、缺失manifest和退休字段`calm_index`。

## 兼容规则

1. `schema_version`不等于`2.1`时失败关闭。
2. 缺失必需字段、非法枚举、非有限数值和正式Mock失败关闭。
3. 已知退休或危险字段按显式规则拒绝。
4. 其他未知字段完成基础校验后由`validate_and_filter`丢弃，不能进入状态推进或渲染接口。
5. 重复`event_id`和非递增`control_seq`由`ControlEventLedger`拒绝，调用方不得推进状态。

## 验证

```powershell
py -3.14 -m pytest "02-技术研发/05-通信协议/tests/contract" -q
```

fixture哈希由项目根目录执行以下命令重建：

```powershell
py -3.14 "02-技术研发/05-通信协议/contracts/generate_fixture_hashes.py"
```
