# F-04 当前执行入口

在仓库根运行 `py -3.14 agent/tasks/F-04/execution/verify_host.py`。
允许执行脚本的PowerShell环境也可运行本目录的 `verify.ps1`；不修改系统执行策略。
它验证当前Python页面模型及T-01交接、生成本轮主机清单、核对历史签收制品身份；不启动TD。

## TD候选重建

先完成上述主机验证。在TD 2025.32820的专用开发工程中，打开Textport执行：

```python
from pathlib import Path
p = Path(r'D:\Agent\srp\agent\tasks\F-04\execution\build_f04_touchdesigner.py')
exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'), dict(globals(), __file__=str(p)))
```

脚本只替换 `/project1/F04_ReadonlyConsole`，新制品写入本包 `outputs/touchdesigner/`，
新运行证据写入 `evidence/touchdesigner/`。等待截图完成后保存、关闭、重新打开新TOE，
按同样方式执行 `verify_f04_touchdesigner_reopen.py`，并再次人工检查导航、曲线与禁用操作。
这些动作会改变当前TD工程，只在专用开发工程执行；历史签署目录不作为输出目标。

共享模型与fixture以agent/modules为权威入口，业务目录迁移及引用修复已验证。
F-04是静态只读示例；T-01负责真实遥测消费，T-02负责请求入口，不由本脚本替代。
