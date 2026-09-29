# MCP 配置指南

> Claude Code 中配置 TouchDesigner + Unity MCP 服务器的完整指南

## 环境实况

| 工具 | 路径 | 版本 |
|------|------|------|
| TouchDesigner | `D:\TouchDesigner\bin\TouchDesigner.exe` | 最新稳定版 |
| Unity | `D:\UnityEngine\6000.4.9f1\Editor\Unity.exe` | 6000.4.9f1 |
| Node.js | `~/.hermes/node/` | ✅ |
| Python | `~/.hermes-venv` | 3.14 |

## 当前项目端口

| 服务 | 地址 | 用途 |
|---|---|---|
| TouchDesigner MCP WebServer | `127.0.0.1:9981` | 开发时操控 TD |
| Unity MCP HTTP | `http://127.0.0.1:8083/mcp` | 开发时操控 Unity |
| Unity MCP health | `http://127.0.0.1:8083/health` | 检查 MCP server 是否运行 |
| Python → TD UDP | `127.0.0.1:5005` | 运行时数据流 |
| Python → Unity UDP | `127.0.0.1:5006` | 运行时数据流 |

## 配置文件体系

Claude Code MCP 配置按优先级（高→低）：

| 优先级 | 路径 | 用途 |
|:------:|------|------|
| 1 | `claude --mcp-config <path>` | 单次调用临时配置 |
| 2 | `.mcp.json`（项目根目录） | 团队共享、git 跟踪 |
| 3 | `~/.claude.json` → `projects.<cwd>.mcpServers` | 当前项目专用 |
| 4 | `~/.claude.json` → `mcpServers` | 全局（所有项目） |
| 5 | `~/.claude/mcp.json` | 旧版全局 |

**重要**：`settings.json` 只管策略（`enableAllProjectMcpServers`、`allowedMcpServers` 等），不定义 MCP server。

---

## 推荐配置方式：项目级 `.mcp.json`

在 03-SRP 根目录创建 `.mcp.json`（可 git 跟踪，全队共享）：

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
    },
    "unity-mcp": {
      "type": "http",
      "url": "http://127.0.0.1:8083/mcp"
    }
  }
}
```

Unity MCP 也可能由 Unity Editor 自动注册到 `~/.claude.json` 的项目路径下；当前项目同时在 `.mcp.json` 固定 HTTP 入口，避免端口漂移。

---

## 安全策略设置

在 `~/.claude/settings.json` 中添加：

```json
{
  "enableAllProjectMcpServers": true,
  "allowedMcpServers": [
    "touchdesigner",
    "unity-mcp"
  ]
}
```

或在项目 `.claude/settings.json` 中单独允许。

---

## 验证与调试

```bash
# 列出所有已注册的 MCP 服务器
claude mcp list

# 查看特定服务器详情
claude mcp list touchdesigner

# 测试连接（如果服务器支持）
claude mcp call touchdesigner get_td_info
```

---

## 常见问题

### Q: MCP 服务器没出现在 claude mcp list 中？
1. 确认配置写在正确文件中（`.mcp.json` 或 `~/.claude.json`）
2. 确认 JSON 语法正确：`cat .mcp.json | python -m json.tool`
3. 重启 Claude Code 会话

### Q: TD 连接超时？
1. 确认 TD 已打开且 WebServer DAT 正在运行（端口 9981）
2. 检查防火墙是否拦截 localhost
3. `npx -y touchdesigner-mcp-server@latest --stdio` 单独运行测试

### Q: Unity relay 路径错误？
1. 确认 `http://127.0.0.1:8083/health` 返回 healthy
2. 确认 Unity Editor 已启动且项目已打开
3. Unity Package Manager 确认 MCPForUnity 已安装
4. 若 RunState 出现在乱码路径，关闭 Unity MCP 后清理该目录并从正确 Unity 项目重新启动 MCP

### Q: npx vs uvx 哪个好？
- `npx`: 不需要安装 Python/uv，Node.js 环境即可（你已有 ~/.hermes/node/）
- `uvx`: Python 生态，依赖 pyproject.toml
- 对 TD MCP：推荐 npx（npm 包更新更快）
