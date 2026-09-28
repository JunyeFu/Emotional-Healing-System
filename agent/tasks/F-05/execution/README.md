# F-05 当前执行入口

在仓库根目录使用PowerShell 7：

```powershell
pwsh -NoProfile -File agent/tasks/F-05/execution/verify.ps1
```

先提交本轮源改动，再从干净工作树运行，以便tested_git_commit准确绑定所测源。
脚本运行合同、P-01与P-02回归，校验v2.2重建、fixture和v2.1不可变项；
当前结果固定写本包evidence/runtime，不覆盖03-测试与实验中的旧封存。
最后复算旧封存的工作树及Git字节，不重写旧签收或原报告。

`Invoke-F05.ps1`的test/verify动作可用于局部开发；仅all产生完整八项证据封存。
证据工具保留原规范化策略和固定叶文件，不给Word或汇总文件追加无消费者的哈希链。
本入口不启动Unity、TD或设备，不发送实验控制。

共享协议仍位于原通信模块；统一业务目录迁移时修正消费者与合同工具路径。
