# 运行协议v1.2到v2.1迁移说明

## 迁移裁定

`UDP字段冻结_v1.2.md`、`udp_sender.py`和`csv_logger.py`保留为历史开发兼容层，不再是正式运行权威。正式链统一消费`contracts/runtime-contract-v2.1.schema.json`，并先经过`runtime_contract.validate_and_filter`。

## 主要变化

| v1.2 | v2.1 |
|---|---|
| 10Hz UDP同时发送TD和Unity | 20Hz自包含遥测，TD为5005、Unity为5006 |
| `version=1.2` | `schema_version=2.1`和显式`message_type` |
| `timestamp`和`meta.frame_id` | 三类单调时间、时钟域、偏移、漂移、不确定度和`frame_seq` |
| 缺失值通常补0或50 | 缺失值为空并带原因码；正式模式不得伪造有效值 |
| `calm_index`可驱动画面 | 仅旧兼容适配器可见，不得进入正式条件、顺序或四层接口 |
| Mock可作为默认来源 | 仅`dev_mock`允许；所有`formal_*`模式失败关闭 |
| UDP承担大部分消息 | TCP 5010承担可靠控制、ACK、回执和请求；UDP只承担实时遥测 |
| 未定义幂等处理 | `event_id`去重且`control_seq`严格递增 |

## 分阶段迁移

1. F-01冻结Schema、fixture和错误语义，不修改会话状态。
2. P-01实现manifest生成、可靠控制服务和状态机，只依赖F-01合同。
3. P-02按合同写入追加式L0/L1并提供确定性重放。
4. U-01和T-01分别消费同一fixture，不复制字段定义。
5. 所有下游完成后删除正式启动路径对v1.2发送器的引用；历史回放通过显式适配器转换，不原地改写L0。

## 失败与回滚

- v2.1消费者遇到v1.2消息时返回`UNSUPPORTED_VERSION`，不得猜测字段含义。
- 开发演示可继续运行v1.2，但必须标注`LEGACY_DEV_ONLY`，不得产生正式证据。
- 若下游尚未迁移，可回退到原v1.2开发入口；v2.1合同文件保持新增，不覆盖历史数据。
