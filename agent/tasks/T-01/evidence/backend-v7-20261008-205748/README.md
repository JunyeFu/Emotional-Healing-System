# P-01 / P-02 后端驱动的 TD 原生演练

两场连续记录均通过：完整固定 A 流程（800 秒有效、10 秒暂停）与 400 秒中止流程。原生截图为 1280×720，30 项页面检查；共 641,300 个采样位置通过源数组、P-02 L0、TD 记录及导出核对。

- [后端封存与重放](backend-report.json)
- [逐样本及导出核对](study-verification.json)
- [原生运行报告](capture-report.json)
- [候选工程](T01_Workbench_A.flow-v5.candidate.toe)
- [运行截图](06-A-motion-rr.png)
- [两场历史记录](25-history.png)
- [返回主页面](29-home-final.png)

实际会话编排和持久化来自 P-01/P-02；设备波形、Unity ACK、前后测回执仍为模拟。没有真实 Unity 渲染回执，也未连接 TCP 5010。固定 A 的开发接线不表示 B 受限适应、新教学流程或正式研究准入已完成。

TD 保存的候选仅包含页面与开发记录功能，Python 后端由[运行命令](../../design/session-backend-v7.md)启动演练。源数据和完整归档保留本机，具体位置见[工作记录](../../../../work/2026-10-08_TD真实Python后端开发联调.md)。
