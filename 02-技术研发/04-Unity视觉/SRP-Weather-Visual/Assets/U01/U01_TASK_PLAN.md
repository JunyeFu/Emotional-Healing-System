# U-01 实现计划与验收清单

## 任务概述
**U-01 【Unity】可靠控制技术探针与渲染回执**

### 交付物
1. **SessionMirror.cs** — 会话状态镜像，从Python控制服务器同步会话状态到Unity
2. **ReliableControlClient.cs** — TCP可靠控制客户端，连接端口5010
3. **UDP5006Gate.cs** — UDP5006接收门，含v2.2合同校验
4. **AckManager.cs** — ACK确认管理，处理事件确认
5. **RenderReceiptManager.cs** — 渲染回执管理，确认渲染完成
6. **ReconnectHandler.cs** — 重连与故障注入逻辑

### 验收标准
- [ ] AC1 丢包/乱序/重复fixture测试通过，控制重发保持同一event_id
- [ ] AC2 旧帧不覆盖新帧，Unity本地时钟不推进模块
- [ ] AC3 握手错误/断连/重连/回执拒绝均按合同失败关闭

### 必需证据
- [ ] Edit/Play测试结果
- [ ] 网络故障日志
- [ ] 状态镜像轨迹
- [ ] ACK与渲染回执序列

### 工作目录
- `D:\Agent\03-SRP\02-技术研发\04-Unity视觉\SRP-Weather-Visual\Assets\U01\`

### 协议参考
- Schema: `D:\Agent\03-SRP\02-技术研发\05-通信协议\contracts\runtime-contract-v2.2.schema.json`
- Python服务端: `D:\Agent\03-SRP\02-技术研发\srp_session_core\transport.py`
- 现有UDPReceiver: `D:\Agent\03-SRP\02-技术研发\04-Unity视觉\SRP-Weather-Visual\Assets\Scripts\UDPReceiver.cs`
