# F-03 Unity 基线入口

从项目根目录运行：

```powershell
pwsh -File Tools/F03/Invoke-F03.ps1 -Mode all
```

可选模式为`verify`、`test`、`build`、`formal-negative`和`all`。构建输出位于Unity工程的`Builds/F03-DevReplay/`并保持Git忽略；验收证据写入`03-测试与实验/evidence/F-03/`。

该入口只形成`DEV-REPLAY`工程、测试和Windows开发构建证据，不实现会话manifest握手、网络传输、四层场景接口或正式运行。
