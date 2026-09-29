# F-01端口登记证据

核验日期：2026-08-07

| 协议与端口 | 绑定 | 职责 | 登记状态 |
|---|---|---|---|
| UDP 5005 | 127.0.0.1 | TD只读20Hz遥测 | 已登记配置占用 |
| UDP 5006 | 127.0.0.1 | Unity 20Hz遥测 | 已登记配置占用 |
| TCP 5010 | 127.0.0.1 | 可靠控制、ACK、渲染回执和TD请求 | 已登记配置预留 |

TCP 5010登记前执行：

```powershell
Get-NetTCPConnection -LocalPort 5010 -State Listen -ErrorAction SilentlyContinue
```

结果为`NO_LISTENER`。该结果只证明登记时没有监听冲突，不证明P-01、U-01或T-02运行链已经实现。全局登记权威为`D:\Agent\全局端口注册表.md`。
