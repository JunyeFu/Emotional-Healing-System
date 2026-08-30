# F-03 Unity 基线入口

从项目根目录运行：

```powershell
pwsh -File Tools/F03/Invoke-F03.ps1 -Mode all
```

可选模式为`verify`、`test`、`build`、`formal-negative`和`all`。构建输出位于Unity工程的`Builds/F03-DevReplay/`并保持Git忽略；验收证据写入`03-测试与实验/evidence/F-03/`。

所有模式都要求运行前Git工作树干净，并记录提交、实现树哈希及运行前后状态。环境锁对文本使用`sha256_lf_no_trailing_ws_text_v1`，因此LF/CRLF检出不构成漂移，其他内容变化仍失败关闭。

`all`会保留`run-1`和`run-2`两份本地构建并逐文件复核哈希，直到第二复核完成；这些约187 MB/份的Git忽略产物不提交仓库。正式门负测试保留同次G-02资产报告和独立F-01必填字段拒绝日志。

该入口只形成`DEV-REPLAY`工程、测试和Windows开发构建证据，不实现会话manifest握手、网络传输、四层场景接口或正式运行。
