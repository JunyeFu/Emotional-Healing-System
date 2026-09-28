# T-01 当前执行入口

仓库根运行`py -3.14 agent/tasks/T-01/execution/verify.py`或本目录verify.ps1。验证48项T-01/F-04专项及9项验证器回归、原23项制品、当前工程清理与已有本轮探针身份。

需要实跑TD时，关闭并保存自己的TD工程，然后运行`run_td_probe.py`。它检查没有其他TD进程和5005占用，只启动隐藏的隔离副本，修改副本回调加入验证钩子，结束时只停止自己启动的进程。运行依赖项目Python与TD2025.32820，不安装依赖、不保存回原工程。输出至本包evidence/runtime，合成输入不作为真实设备证据。

旧Text TOP可读性候选由`repair_readonly_layout.py`产生，已有候选时拒绝覆盖。随后`run_td_probe.py --readable`实跑该候选，主Agent另检查五张截图。它不是A主题实现。

## TD内完整重建

在专用开发工程Textport中执行：

```python
from pathlib import Path
p = Path(r'D:\Agent\srp\agent\tasks\T-01\execution\build_t01_touchdesigner.py')
exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'), dict(globals(), __file__=str(p)))
```

只重建/project1/T01_TelemetryPanel，新TOE/TOX及host/touchdesigner证据写本包evidence/runtime。实际重开新TOE后同样执行verify_t01_touchdesigner_reopen.py；replay_t01_udp.py负责发送，不放在正式只读制品中。完整23件新运行证据齐备后才运行generate_evidence_manifest.py，不生成或修改历史清单。

`build_workbench_a.py`使用同样执行方式，只允许原模块或本包runtime中的专用工程；保存独立A主题候选，不覆盖原签收制品。它尚未通过本轮TD原生控件验证，不把主机回调编译测试算作UI验收。
