# TouchDesigner MCP 操作手册

> 方案：8beeeaaat/touchdesigner-mcp v1.4.7 | 12 工具 | MIT 许可证
> 仓库：https://github.com/8beeeaaat/touchdesigner-mcp
> 通信：WebServer DAT ← HTTP → MCP Server → Claude Code

## 架构

```
┌──────────────────┐   HTTP (9981)   ┌──────────────────┐   MCP    ┌──────────────┐
│  TouchDesigner   │ ◄──────────────►│  MCP Server      │ ◄───────►│  Claude Code │
│  WebServer DAT   │                 │  (npx / uvx)     │          │              │
│  + callbacks.py  │                 │  touchdesigner-  │          │              │
│                  │                 │  mcp-server      │          │              │
└──────────────────┘                 └──────────────────┘          └──────────────┘
```

## 安装

### 1. TD 侧：安装 WebServer DAT

在 TouchDesigner 中：
1. 打开你的 .toe 工程
2. 按 TAB → 搜索 `WebServer` → 拖入
3. 设置 WebServer DAT 参数：
   - Port: `9981`
   - Active: `On`
4. 下载 `touchdesigner-mcp` 仓库中的 `td_mcp_callbacks.py`
5. 在 WebServer DAT 的 Callbacks 页签中加载该脚本
6. 确认 WebServer 状态为 "Running"

### 2. Claude Code 侧：配置 MCP Server

**方案 A：npx（推荐，无需安装）**

在 `~/.claude.json` 中添加：
```json
{
  "mcpServers": {
    "touchdesigner": {
      "command": "npx",
      "args": ["-y", "touchdesigner-mcp-server@latest", "--stdio"],
      "env": {
        "TD_HOST": "127.0.0.1",
        "TD_PORT": "9981"
      }
    }
  }
}
```

**方案 B：Claude Code CLI 一键添加**
```bash
claude mcp add touchdesigner -- npx -y touchdesigner-mcp-server@latest --stdio
```

**方案 C：uvx**
```json
{
  "mcpServers": {
    "touchdesigner": {
      "command": "uvx",
      "args": ["touchdesigner-mcp-server"],
      "env": {
        "TD_HOST": "127.0.0.1",
        "TD_PORT": "9981"
      }
    }
  }
}
```

### 3. 验证连接

在 Claude Code 中执行：
```
claude mcp list
```
应看到 `touchdesigner` 服务器已连接。

---

## 完整工具 API

### 1. create_td_node — 创建节点

创建新的 TouchDesigner 算子。

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `operatorType` | string | ✅ | TD 算子类型，如 `container`、`text`、`constant`、`oscin`、`panel` |
| `parentPath` | string | ✅ | 父节点路径，如 `/project1` |
| `name` | string | | 节点名称，不指定则自动生成 |
| `parameters` | object | | 初始化参数字典，如 `{"text": "hello"}` |

示例：创建 UDP 接收 DAT
```
create_td_node(operatorType="oscin", parentPath="/project1", name="udp_in", parameters={"port": 5005})
```

---

### 2. delete_td_node — 删除节点

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `path` | string | ✅ | 节点完整路径，如 `/project1/old_node` |

示例：
```
delete_td_node(path="/project1/temp_container")
```

---

### 3. get_td_nodes — 获取节点列表

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `parentPath` | string | | 父路径，默认 `/` |
| `filter` | string | | 过滤节点类型名称 |

示例：
```
get_td_nodes(parentPath="/project1", filter="container")
```

---

### 4. get_td_node_parameters — 获取节点参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `path` | string | ✅ | 节点路径 |

返回节点的所有参数名和当前值。

---

### 5. update_td_node_parameters — 更新节点参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `path` | string | ✅ | 节点路径 |
| `parameters` | object | ✅ | 要更新的参数键值对 |

示例：
```
update_td_node_parameters(path="/project1/udp_in", parameters={"port": 5005, "active": true})
```

---

### 6. exec_node_method — 调用节点方法

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `path` | string | ✅ | 节点路径 |
| `methodName` | string | ✅ | Python 方法名 |
| `args` | array | | 位置参数 |
| `kwargs` | object | | 关键字参数 |

示例：
```
exec_node_method(path="/project1/my_op", methodName="copy", kwargs={"name": "my_op_copy"})
```

---

### 7. execute_python_script — 执行 Python 脚本

在 TouchDesigner 上下文中执行任意 Python。这是最强大的工具——可以一次性创建复杂节点网络。

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `script` | string | ✅ | Python 代码字符串 |

示例：
```python
# 创建 SRP 呼吸引导骨架
parent = op('/project1')
container = parent.create(containerCOMP, 'breath_guide')
# 创建 UPD In DAT
udp_in = container.create(oscinDAT, 'udp_in')
udp_in.par.port = 5005
# 创建 Execute DAT 处理数据
exec_dat = container.create(textDAT, 'process_data')
```

---

### 8. get_td_node_errors — 检查节点错误

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `path` | string | ✅ | 节点路径 |

返回该节点及其子节点的错误信息。

---

### 9. get_td_info — TD 环境信息

无参数。返回 TD 版本、Python 版本、工程路径等信息。

---

### 10. get_td_classes — 获取 TD 类列表

无参数。列出所有 TouchDesigner Python API 类。

---

### 11. get_td_class_details — 获取类详情

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `className` | string | ✅ | TD Python 类名 |

---

### 12. get_module_help — 获取 Python 帮助

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `moduleName` | string | ✅ | 模块或类名 |

---

## SRP 项目典型工作流

### 工作流 1：一次性创建呼吸引导圈骨架

```
execute_python_script(script="""
# 创建 SRP 主容器
root = op('/project1')
srp = root.create(containerCOMP, 'srp_main')

# UDP 输入
udp_in = srp.create(oscinDAT, 'udp_in')
udp_in.par.port = 5005

# JSON 解析 Execute DAT
parser = srp.create(textDAT, 'json_parser')
parser.par.text = '''
import json

def onReceiveOSC(dat, rowIndex, message, bytes):
    data = json.loads(message[1])
    # 提取4维评分字段并驱动 CHOP
    scores = data.get('scores', {})
    calm_index = data.get('calm_index', 50)
    breath = data.get('breath', {})
    
    # 写入常量 CHOP 供后续动画使用
    op('breath_sync_par').par.value0 = scores.get('breath_sync', 0)
    op('breath_depth_par').par.value0 = scores.get('breath_depth', 0)
    op('hrv_coherence_par').par.value0 = scores.get('hrv_coherence', 0)
    op('eda_calm_par').par.value0 = scores.get('eda_calm', 0)
    op('calm_index_par').par.value0 = calm_index
'''

# CHOP 用于驱动参数 (4-dim)
srp.create(constantCHOP, 'breath_sync_par')
srp.create(constantCHOP, 'breath_depth_par')
srp.create(constantCHOP, 'hrv_coherence_par')
srp.create(constantCHOP, 'eda_calm_par')
srp.create(constantCHOP, 'calm_index_par')
srp.create(constantCHOP, 'target_phase')

# 呼吸引导圈 (Circle SOP + Transform CHOP)
circle = srp.create(circleSOP, 'guide_circle')
circle_transform = srp.create(transformCHOP, 'circle_transform')
circle_transform.par.scale = 0.5

# 监控台 Panel
monitor = srp.create(panelCOMP, 'monitor_panel')

# 实时曲线
curve = srp.create(trailCHOP, 'breath_curve')
""")
```

### 工作流 2：调试——查看节点状态

```
get_td_node_errors(path="/project1/srp_main")
get_td_node_parameters(path="/project1/srp_main/udp_in")
```

### 工作流 3：修改引导圈动画参数

```
update_td_node_parameters(
  path="/project1/srp_main/circle_transform",
  parameters={"scale": 0.8, "tx": 0.5}
)
```

---

## 已知限制

1. **单线程**：Python 脚本在 TD 主线程执行，耗时操作会卡 UI
2. **WebServer 依赖**：必须先在 TD 中手动启动 WebServer DAT
3. **无二进制传输**：只能传文本，不能直接传图像/TOX 文件
4. **路径区分大小写**：TD 节点路径严格区分大小写
5. **错误恢复**：脚本执行失败不会自动回滚节点创建

## 与现有 OSC 方案的关系

```
现有方案：外部 Python → OSC UDP:7000 → TD OSC In DAT (运行时操控)
MCP 方案：Claude Code → HTTP → TD WebServer DAT (开发时搭建)

两者共存：MCP 搭建初始骨架 → OSC 做运行时微调
```
