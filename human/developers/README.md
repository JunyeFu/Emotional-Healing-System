# 开发上手

先验证不依赖设备的Python底座，再进入所属工程。当前没有统一正式启动器。

## 取得源码

```powershell
git clone --branch codex/td-workbench-readability https://github.com/JunyeFu/Emotional-Healing-System.git srp
Set-Location srp
git lfs install --local
git lfs pull
```

已有工作区直接从仓库根执行后续命令，不覆盖已有改动。固定公开版本见[GitHub默认首页](https://github.com/JunyeFu/Emotional-Healing-System)。

## Python首次验证

前提：Python 3.14及Git LFS。依赖见[requirements.txt](https://github.com/JunyeFu/Emotional-Healing-System/blob/d2245d4dee7916f898be2ff872a2062b6617ee92/agent/modules/requirements.txt)，版本依据见[依赖基线](https://github.com/JunyeFu/Emotional-Healing-System/blob/d2245d4dee7916f898be2ff872a2062b6617ee92/agent/modules/requirements-baseline-py3.14.txt)。新成员使用独立虚拟环境。

```powershell
py -3.14 -m venv agent/local/venv
agent/local/venv/Scripts/python.exe -m pip install -r agent/modules/requirements.txt
agent/local/venv/Scripts/python.exe -m pytest agent/modules/tests/session_core agent/modules/tests/session_store -q
```

已有项目依赖时可直接运行：

```powershell
py -3.14 -m pytest agent/modules/tests/session_core agent/modules/tests/session_store -q
```

成功表现：定向测试全部通过，覆盖会话状态与追加记录/重放；不需要设备或编辑器。这不是Unity/TD或真实设备全链验收。全仓既有失败见[验证日志](https://github.com/JunyeFu/Emotional-Healing-System/blob/d2245d4dee7916f898be2ff872a2062b6617ee92/agent/work/codex-verification-log.md)。

## 选择开发模块

| 工作 | 源码与合同 | 操作起点 |
|---|---|---|
| 会话流程与时钟 | [SessionCore](https://github.com/JunyeFu/Emotional-Healing-System/blob/d2245d4dee7916f898be2ff872a2062b6617ee92/agent/modules/srp_session_core/README.md) | `agent/modules/srp_session_core/`与定向测试 |
| 记录与重放 | [P-02交接](https://github.com/JunyeFu/Emotional-Healing-System/blob/d2245d4dee7916f898be2ff872a2062b6617ee92/agent/tasks/P-02/outputs/current-store-contract.md) | `agent/modules/srp_session_store/` |
| 设备采集 | [采集模块](https://github.com/JunyeFu/Emotional-Healing-System/blob/d2245d4dee7916f898be2ff872a2062b6617ee92/agent/modules/acquisition/README.md) | D-01/D-02任务及专用SDK输入 |
| 交互状态估计 | [信号模块](https://github.com/JunyeFu/Emotional-Healing-System/blob/d2245d4dee7916f898be2ff872a2062b6617ee92/agent/modules/signal-processing/README.md) | S-01/S-02任务；旧评分不替代新算法 |
| Unity画面 | [U-03交接](https://github.com/JunyeFu/Emotional-Healing-System/blob/d2245d4dee7916f898be2ff872a2062b6617ee92/agent/tasks/U-03/outputs/current-slice.md) | Unity Hub添加 `agent/modules/unity/SRP-Weather-Visual/` |
| TD操作台 | [T-01任务](https://github.com/JunyeFu/Emotional-Healing-System/blob/d2245d4dee7916f898be2ff872a2062b6617ee92/agent/tasks/T-01/TASK.md) | `agent/modules/touchdesigner/`；按合同打开候选工程 |
| 接口与消息 | [通信合同](https://github.com/JunyeFu/Emotional-Healing-System/blob/d2245d4dee7916f898be2ff872a2062b6617ee92/agent/modules/communication/contracts/README.md) | 先读合同，再改发送端/消费端 |

Unity团队目标2022.3.62f3，但共享工程 `ProjectVersion.txt` 当前仍为6000.4.9f1，迁移未验收；不要用旧编辑器直接覆盖共享工程。TD目标2025.32820。原生工程与真实运行按所属任务分别验收。

## 接着做

从[任务导航](../tasks/README.md)选择解锁包，按快照和交付位置修改。任务工具在 `agent/tasks/<编号>/execution/`，通用实现放 `agent/modules/`。见[协作指南](../../CONTRIBUTING.md)与[目录规范](../project/repository-layout.md)。
