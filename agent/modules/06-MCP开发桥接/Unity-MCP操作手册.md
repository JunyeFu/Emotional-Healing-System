# Unity MCP 操作手册

> 方案：CoplayDev/unity-mcp v9.7.0 | 40+ 工具 | MIT 许可证
> 仓库：https://github.com/CoplayDev/unity-mcp
> 通信：Unity Editor ← relay binary → MCP Bridge → Claude Code

## 架构

```
┌──────────────────┐   localhost    ┌──────────────────┐   MCP    ┌──────────────┐
│  Unity Editor    │ ◄─────────────►│  MCP Bridge       │ ◄───────►│  Claude Code │
│  + MCPForUnity   │   relay.exe    │  (Python)         │          │              │
│  package         │                │                   │          │              │
└──────────────────┘                └──────────────────┘          └──────────────┘
```

---

## 安装

### 1. Unity 侧：安装 MCPForUnity 包

在 Unity 编辑器中：
1. Window → Package Manager → + → Add package from git URL
2. 输入：`https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main`
3. 等待导入完成
4. 菜单栏出现 `MCP` 菜单项

### 2. Claude Code 侧：配置 MCP

Unity MCP 工具会自动注册到 `~/.claude.json`。在 Unity 中：
1. Project Settings → AI → Unity MCP → Integrations
2. 点击 "Configure Claude Code"
3. 自动写入配置

手动配置：
```json
{
  "projects": {
    "C:/Users/fujunye/Desktop/Hermes/03-SRP": {
      "mcpServers": {
        "unity-mcp": {
          "type": "stdio",
          "command": "<user_home>/.unity/relay/relay_win.exe",
          "args": ["--mcp"],
          "env": {}
        }
      }
    }
  }
}
```

### 3. 验证连接

在 Claude Code 中：
```
claude mcp list
```
应看到 `unity-mcp` 服务器，包含 40+ 工具。

---

## SRP 核心工具速查

以下是与 03-SRP 项目直接相关的工具（按使用频率排序）。

### 场景管理：manage_scene

| 常用 action | 说明 |
|-------------|------|
| `create` | 创建新场景（支持 scene_template: `2d_basic`） |
| `load` | 加载场景 |
| `save` | 保存场景 |
| `get_hierarchy` | 获取场景层级结构 |
| `screenshot` | 截取 Game 视图（`batch=surround` 6方向） |

SRP 用例：
```
manage_scene(action="create", name="StormScene", scene_template="2d_basic")
manage_scene(action="screenshot", batch="single")
```

---

### GameObject 管理：manage_gameobject

| 常用 action | 说明 |
|-------------|------|
| `create` | 创建 GameObject（可指定 name、parent、components） |
| `modify` | 修改 Transform、Tag、Layer、active 等 |
| `delete` | 删除 |
| `duplicate` | 复制 |
| `find` | 按名称/标签/组件查找 |
| `set_parent` | 设置父子关系 |
| `get_components` | 列出所有组件 |

SRP 用例：
```
# 创建旅人 Sprite
manage_gameobject(action="create", name="Traveler", components=["SpriteRenderer"])
# 创建天气粒子系统父节点
manage_gameobject(action="create", name="WeatherParticles", components=[])
# 设置位置
manage_gameobject(action="modify", name="Traveler", transform={"position": [0, 0, 0]})
```

---

### 脚本管理：create_script + script_apply_edits

**create_script** — 创建 C# 脚本：
| 参数 | 说明 |
|------|------|
| `path` | 脚本路径，如 `Assets/Scripts/OSCReceiver.cs` |
| `template` | 模板类型（可选） |

**script_apply_edits** — 结构化编辑 C# 代码：
| edit_type | 说明 |
|-----------|------|
| `insert` | 在指定位置插入代码 |
| `replace` | 替换指定方法/类 |
| `delete` | 删除代码块 |

SRP 用例——创建 OSCReceiver.cs：
```
create_script(path="Assets/Scripts/OSCReceiver.cs")
script_apply_edits(
  script_path="Assets/Scripts/OSCReceiver.cs",
  edits=[{
    "edit_type": "replace",
    "target": "class_body",
    "new_code": "// UDP client receiving JSON data on port 5006\n// Parse and dispatch to WeatherController"
  }]
)
```

---

### 组件管理：manage_components

SRP 用例：
```
# 给旅人添加 Animator
manage_components(action="add", target="Traveler", component="Animator")
# 设置 SpriteRenderer 参数
manage_components(action="modify", target="Traveler.SpriteRenderer", properties={"sprite": "...", "color": [1,1,1,1]})
```

---

### 资源管理：manage_asset + manage_material

**manage_asset** 常用 action：`import`、`create`、`search`、`rename`、`delete`

SRP 用例：
```
# 导入旅人 Sprite 图片
manage_asset(action="import", path="Assets/Sprites/traveler_idle.png")
# 创建材质
manage_material(action="create", name="TravelerMaterial", shader="Sprites/Default")
```

---

### 预制体：manage_prefabs

SRP 用例：
```
# 把旅人做成 prefab
manage_prefabs(action="create", source="Traveler", path="Assets/Prefabs/Traveler.prefab")
# 在场景中实例化
manage_prefabs(action="instantiate", prefab="Assets/Prefabs/Traveler.prefab", position=[0, 0, 0])
```

---

### 相机管理：manage_camera

预设模式（7种）：
| preset | 适用 |
|--------|------|
| `side_scroller` | 2D 横板（SRP 默认） |
| `top_down` | 俯视 |
| `static` | 固定视角 |

SRP 用例：
```
manage_camera(action="apply_preset", preset="side_scroller")
manage_camera(action="screenshot")
```

---

### UI 管理：manage_ui

SRP 用例——创建天气强度文字显示：
```
manage_ui(action="create_canvas")
manage_ui(action="add_text", parent="Canvas", name="WeatherStatus", text="风暴 · 逐渐减弱")
manage_ui(action="add_slider", parent="Canvas", name="BreathIndicator", min=0, max=100)
```

---

### 粒子系统：manage_vfx

SRP 用例——创建雨滴粒子：
```
manage_gameobject(action="create", name="RainParticles", components=["ParticleSystem"])
manage_vfx(action="configure", target="RainParticles", preset="rain")
```

---

### 动画管理：manage_animation

SRP 用例——旅人状态机：
```
manage_animation(action="create_animator_controller", name="TravelerAnimator")
manage_animation(action="add_state", controller="TravelerAnimator", state="Walk")
manage_animation(action="add_state", controller="TravelerAnimator", state="Protected")
manage_animation(action="add_transition", from="Walk", to="Protected", condition="weather_intensity > 0.7")
```

---

### 批量操作：batch_execute

一次性执行多个操作（10-100x 更快）：
```
batch_execute(actions=[
  {"tool": "manage_scene", "args": {"action": "create", "name": "StormScene", "scene_template": "2d_basic"}},
  {"tool": "manage_gameobject", "args": {"action": "create", "name": "Traveler", "components": ["SpriteRenderer", "Animator"]}},
  {"tool": "manage_camera", "args": {"action": "apply_preset", "preset": "side_scroller"}},
  {"tool": "manage_gameobject", "args": {"action": "create", "name": "BG_Storm", "components": ["SpriteRenderer"]}},
  {"tool": "manage_gameobject", "args": {"action": "create", "name": "RainParticles", "components": ["ParticleSystem"]}}
])
```

---

### 编辑器与调试

| 工具 | 用途 |
|------|------|
| `manage_editor` | 进入/退出 Play 模式、undo/redo、设置标签 |
| `read_console` | 读取 Console 日志、清空 |
| `execute_menu_item` | 执行菜单命令（如 `File/Save Project`） |
| `refresh_unity` | 刷新资源数据库 + 编译 |
| `manage_profiler` | 性能分析 |

---

## SRP 四场景批量创建流程

```
# 步骤 1：创建 4 个场景
for weather in ["Storm", "Heat", "Snow", "Fade"]:
    manage_scene(action="create", name=f"{weather}Scene", scene_template="2d_basic")
    manage_camera(action="apply_preset", preset="side_scroller")
    manage_gameobject(action="create", name="Traveler", components=["SpriteRenderer"])
    manage_gameobject(action="create", name=f"Particles_{weather}", components=["ParticleSystem"])
    manage_scene(action="save")

# 步骤 2：创建共享脚本（当前打开的场景）
create_script(path="Assets/Scripts/OSCReceiver.cs")
create_script(path="Assets/Scripts/WeatherController.cs")
create_script(path="Assets/Scripts/TravelerAnim.cs")
create_script(path="Assets/Scripts/TransitionManager.cs")

# 步骤 3：在场景中挂载脚本
manage_components(action="add", target="MainCamera", component="OSCReceiver")
manage_components(action="add", target="MainCamera", component="WeatherController")
manage_components(action="add", target="Traveler", component="TravelerAnim")
manage_components(action="add", target="MainCamera", component="TransitionManager")

# 步骤 4：验证——截图
manage_scene(action="screenshot")
read_console()  # 检查编译错误
```

---

## 已知限制

1. **必须 Unity Editor 打开**：不是 headless 模式，可视化操作才能生效
2. **Windows relay 路径**：中文或空格路径可能导致 relay.exe 启动失败
3. **编译等待**：`create_script` 后需要等编译完成再挂载组件——用 `read_console` 检查编译状态
4. **2D 模板**：`scene_template="2d_basic"` 需要 Unity 2D 模块已安装
5. **batch_execute 限制**：某些操作（如 `manage_scene(create)` 后紧跟 `manage_gameobject`）需要场景先加载完

## 与现有 UDP 方案的关系

```
现有方案：Python → UDP:5006 → OSCReceiver.cs → WeatherController.cs
MCP 方案：Claude Code → relay → Unity Editor（创建脚本、场景、预制体）

MCP 负责把 OSCReceiver.cs、WeatherController.cs 等脚本写出来，
并搭建好场景结构，然后运行时数据流仍走 UDP。
```
