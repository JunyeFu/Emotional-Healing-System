# OSC Bridge — TouchDesigner 远程遥控桥接

通过 OSC 协议从外部 Python 脚本远程操控 TouchDesigner，支持参数设置、脚本执行、节点创建/删除、工程保存等操作。

## 架构

```
外部 Python (hermes-venv)           TouchDesigner
┌────────────────────┐    OSC     ┌──────────────────────┐
│  osc_controller.py │ ──UDP:7000→│ OSC In DAT (oscin1)  │
│                    │           │ Execute DAT (exec_osc)│
│  par / exec / create│           │ td.op().par().val     │
└────────────────────┘           └──────────────────────┘
```

## 环境准备

```bash
# 激活 hermes 虚拟环境
source ~/.hermes-venv/bin/activate

# 安装 python-osc
pip install python-osc
```

## TD 侧配置（一次性）

### 方案 A：WebServer DAT（推荐 — Claude Code 可直连）

1. 在 TD 中确认 WebServer DAT 已放置（TAB → WebServer）
2. 设置 port = `9980`，Active = `On`
3. 打开 `td_webserver_callbacks.py`，全选复制
4. 在 WebServer DAT 的 **Callbacks** 页签中粘贴
5. 确认 TD Console 输出 `[WebServer Callbacks] SRP TD Bridge ready`

**API 端点**：

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/status` | 工程信息 + 根节点列表 |
| GET | `/nodes?path=/project1` | 列出子节点 |
| POST | `/exec` `{"script":"..."}` | 执行 Python |
| POST | `/inspect` `{"parent":"/project1"}` | 递归导出完整节点树 |
| POST | `/params` `{"path":"..."}` | 读取参数 |
| POST | `/params/set` `{"path":"..","params":{}}` | 设置参数 |
| POST | `/node/create` `{"parent":"..","type":"..","name":".."}` | 创建节点 |
| GET | `/errors?path=/project1` | 检查节点错误 |

### 方案 B：OSC In DAT（已有 — 仍需 Execute DAT）

1. 确认 OSC In DAT 已放置 → port `7000`
2. 拖入 Execute DAT → 命名 `exec_osc`
3. 将 `td_osc_receiver.py` 内容粘贴到 Execute DAT 中
4. 将 Execute DAT 的 **Monitor** 参数设为 `On`

## 外部操控

### CLI 模式

```bash
# 测试连通性
python osc_controller.py ping

# 执行 TD Python 代码
python osc_controller.py exec "app.setStep(60)"

# 设置参数
python osc_controller.py par /project1/monitor/breath_circle opacity 0.8

# 创建节点
python osc_controller.py create /project1 container my_comp

# 删除节点
python osc_controller.py delete /project1/my_comp

# 触发脉冲参数
python osc_controller.py pulse /project1/button1 reset

# 加载 tox 组件
python osc_controller.py load /project1 path/to/breath_guide.tox

# 保存工程
python osc_controller.py save
```

### 互动模式

```bash
python osc_controller.py

osc> ping
osc> srp          # 一键搭建 SRP 工程骨架
osc> osc          # 搭建 OSC 接收链
osc> help         # 查看所有命令
osc> quit
```

### SRP 一键骨架

```bash
python osc_controller.py srp
```

自动创建以下节点树：

```
/project1
├── udp_in            (DAT — UDP 数据接收)
├── monitor           (Container)
│   ├── breath_circle
│   ├── prompt_display
│   └── dashboard
├── weather_viz       (Container)
└── data_curve        (Container)
```

## 支持的 OSC 地址

| OSC 地址 | 参数 | 功能 |
|----------|------|------|
| `/td/exec` | `<script>` | 执行 TD Python 代码 |
| `/td/par/set` | `<path> <par> <val>` | 设置参数值 |
| `/td/par/get` | `<path> <par> [callback]` | 读取参数值 |
| `/td/op/create` | `<parent> <type> [name]` | 创建算子 |
| `/td/op/delete` | `<path>` | 删除算子 |
| `/td/op/select` | `<path>` | 选中算子 |
| `/td/pulse` | `<path> <par>` | 触发脉冲参数 |
| `/td/file/load` | `<path> <file>` | 加载 tox 文件 |
| `/td/project/save` | `[filepath]` | 保存工程 |
| `/td/quit` | — | 退出 TD |
| `/td/ping` | — | 连通性测试 |

## 故障排查

| 问题 | 检查 |
|------|------|
| OSC 消息无响应 | OSC In DAT port 是否为 7000，Execute DAT Monitor 是否开启 |
| `ping` 无 `pong` 返回 | TD 工程是否已加载，防火墙是否放行 UDP 7000 |
| `python-osc` 导入失败 | 确认 `pip install python-osc` 在 hermes-venv 中执行 |
| `srp` 命令报错 | TD 工程必须已打开，`/project1` 路径必须存在 |
