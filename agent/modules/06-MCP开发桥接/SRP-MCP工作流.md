# SRP MCP 工作流 — Claude Code 端到端搭建

> 从零开始：模拟数据就绪后，用 MCP 一次性搭建 TD 监控台 + Unity 天气场景
> **架构 (6/2)**: TD渲染呼吸引导圈 → Spout推送纹理 → Unity展示为背景层。TD=渲染+监控，Unity=展示+体验。

## 前提条件

- [x] Python 信号管道可运行（`main.py` 或模拟数据脚本）
- [ ] TouchDesigner 已安装 + WebServer DAT 端口 9980
- [ ] Unity 6000.4.9f1+ 已安装 + MCPForUnity 包已导入
- [ ] `.mcp.json` 已配置 TD MCP + Unity MCP

---

## 阶段 A：TouchDesigner — 呼吸引导圈渲染 + Spout 推送 + 监控台

### A1. 验证连接 + 查看环境

```
get_td_info
get_td_nodes(parentPath="/")
```

### A2. 创建 SRP TD 骨架

用 `execute_python_script` 一次性创建完整节点树：

```python
# === SRP TD 骨架（呼吸引导圈 + Spout Out + 监控台 + 曲线） ===
root = op('/project1')
srp = root.create(containerCOMP, 'SRP')

# -- 子容器 --
udp_block = srp.create(containerCOMP, 'UDP_Input')
guide_block = srp.create(containerCOMP, 'BreathGuide')
monitor_block = srp.create(containerCOMP, 'MonitorPanel')
curve_block = srp.create(containerCOMP, 'DataCurves')

# -- UDP 输入 --
udp_in = udp_block.create(udpinDAT, 'udp_in')
udp_in.par.port = 5005
udp_in.par.active = True

# -- JSON 解析 + 数据分发 --
exec_script = udp_block.create(textDAT, 'json_dispatcher')
exec_script.par.text = '''
import json

def onRowChange(dat, rows):
    data = json.loads(dat[0, 0])
    scores = data.get('scores', {})
    breath = data.get('breath', {})
    cardiac = data.get('cardiac', {})
    guidance = data.get('guidance', {})
    calm_index = data.get('calm_index', 50)

    parent = op('json_dispatcher').parent().parent()
    parent.op('BreathGuide/circle_radius').par.value0 = guidance.get('circle_radius', 0.5)
    parent.op('BreathGuide/phase').par.value0 = {'inhale': 0, 'hold': 1, 'exhale': 2}.get(breath.get('phase', 'inhale'), 0)
    parent.op('MonitorPanel/calm_index_par').par.value0 = calm_index
    parent.op('MonitorPanel/breath_sync_par').par.value0 = scores.get('breath_sync', 0)
    parent.op('MonitorPanel/breath_depth_par').par.value0 = scores.get('breath_depth', 0)
    parent.op('MonitorPanel/hrv_coherence_par').par.value0 = scores.get('hrv_coherence', 0)
    parent.op('MonitorPanel/eda_calm_par').par.value0 = scores.get('eda_calm', 0)
    parent.op('MonitorPanel/hr_par').par.value0 = cardiac.get('hr', 0)
    parent.op('MonitorPanel/rr_par').par.value0 = breath.get('rate', 0)
    parent.op('DataCurves/hr_par').par.value0 = cardiac.get('hr', 0)
    parent.op('DataCurves/rr_par').par.value0 = breath.get('rate', 0)
'''

# -- 呼吸引导圈 --
guide_block.create(constantCHOP, 'circle_radius')
guide_block.create(constantCHOP, 'phase')
circle = guide_block.create(circleSOP, 'guide_circle')
circle_transform = guide_block.create(transformCHOP, 'circle_anim')
circle_render = guide_block.create(renderTOP, 'circle_render')

# -- Spout Out（推送呼吸圈纹理到 Unity）--
spout_out = guide_block.create(spoutoutTOP, 'spout_out')
spout_out.par.sender = 'SRP_BreathCircle'

# -- 监控台（4维评分 + calm_index + HR + RR）--
monitor_block.create(constantCHOP, 'calm_index_par')
monitor_block.create(constantCHOP, 'breath_sync_par')
monitor_block.create(constantCHOP, 'breath_depth_par')
monitor_block.create(constantCHOP, 'hrv_coherence_par')
monitor_block.create(constantCHOP, 'eda_calm_par')
monitor_block.create(constantCHOP, 'hr_par')
monitor_block.create(constantCHOP, 'rr_par')
panel = monitor_block.create(panelCOMP, 'monitor_panel')

# -- 实时曲线 --
curve_block.create(constantCHOP, 'hr_par')
curve_block.create(constantCHOP, 'rr_par')
hr_trail = curve_block.create(trailCHOP, 'hr_trail')
rr_trail = curve_block.create(trailCHOP, 'rr_trail')

print("SRP TD 骨架创建完成（呼吸圈 + Spout + 监控台 + 曲线）！")
```

### A3. 验证骨架

```
get_td_node_errors(path="/project1/SRP")
get_td_nodes(parentPath="/project1/SRP")
```

---

## 阶段 B：Unity — Spout 接收呼吸圈 + 全部天气视觉 + 旅人 + 环境提示词

### B1. 验证连接 + 查看环境

```
manage_scene(action="get_hierarchy")
read_console()
```

### B2. 创建风暴场景 + 脚本

```
batch_execute(actions=[
  # -- 场景 --
  {"tool": "manage_scene", "args": {"action": "create", "name": "StormScene", "scene_template": "2d_basic"}},

  # -- 核心脚本 --
  {"tool": "create_script", "args": {"path": "Assets/Scripts/UDPReceiver.cs"}},
  {"tool": "create_script", "args": {"path": "Assets/Scripts/SpoutReceiver.cs"}},
  {"tool": "create_script", "args": {"path": "Assets/Scripts/WeatherController.cs"}},
  {"tool": "create_script", "args": {"path": "Assets/Scripts/TravelerAnim.cs"}},
  {"tool": "create_script", "args": {"path": "Assets/Scripts/PromptDisplay.cs"}},

  # -- 目录结构 --
  {"tool": "manage_asset", "args": {"action": "create_folder", "path": "Assets/Sprites"}},
  {"tool": "manage_asset", "args": {"action": "create_folder", "path": "Assets/Animations"}},
  {"tool": "manage_asset", "args": {"action": "create_folder", "path": "Assets/Particles"}},
])
```

### B3. 编辑 UDPReceiver.cs

```
script_apply_edits(
  script_path="Assets/Scripts/UDPReceiver.cs",
  edits=[{
    "edit_type": "replace",
    "target": "class_body",
    "new_code": '''
using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

public class UDPReceiver : MonoBehaviour
{
    private UdpClient udpClient;
    private Thread receiveThread;
    [SerializeField] private int port = 5006;

    public System.Action<string> OnMessageReceived;

    void Start()
    {
        udpClient = new UdpClient(port);
        receiveThread = new Thread(ReceiveLoop);
        receiveThread.IsBackground = true;
        receiveThread.Start();
    }

    void ReceiveLoop()
    {
        IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, port);
        while (true)
        {
            try
            {
                byte[] data = udpClient.Receive(ref remoteEndPoint);
                string json = Encoding.UTF8.GetString(data);
                // 主线程回调
            }
            catch (System.Exception e) { Debug.LogWarning($"UDP: {e.Message}"); }
        }
    }

    void Update()
    {
        // 在主线程处理接收到的消息
    }

    void OnDestroy()
    {
        receiveThread?.Abort();
        udpClient?.Close();
    }
}
'''
  }]
)
```

### B4. 编辑 SpoutReceiver.cs — 接收 TD Spout 纹理展示为背景层

```
script_apply_edits(
  script_path="Assets/Scripts/SpoutReceiver.cs",
  edits=[{
    "edit_type": "replace",
    "target": "class_body",
    "new_code": '''
using UnityEngine;
using Klak.Spout;

public class SpoutReceiver : MonoBehaviour
{
    [SerializeField] private string senderName = "SRP_BreathCircle";
    private Klak.Spout.SpoutReceiver receiver;
    private Material displayMaterial;

    void Start()
    {
        receiver = GetComponent<Klak.Spout.SpoutReceiver>();
        if (!receiver) receiver = gameObject.AddComponent<Klak.Spout.SpoutReceiver>();
        receiver.sourceName = senderName;

        var renderer = GetComponent<Renderer>();
        if (renderer)
        {
            displayMaterial = renderer.material;
            // 设置透明度混合（呼吸圈叠加在背景色之上）
            displayMaterial.SetInt("_ZWrite", 0);
            displayMaterial.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            displayMaterial.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        }
    }
}
'''
  }]
)
```

### B5. 编辑 WeatherController.cs — 包含全部天气视觉映射

```
script_apply_edits(
  script_path="Assets/Scripts/WeatherController.cs",
  edits=[{
    "edit_type": "replace",
    "target": "class_body",
    "new_code": '''
using UnityEngine;

[System.Serializable]
public class SRPData
{
    public float calm_index;
    public WeatherInfo weather;
    public BreathInfo breath;
    public GuidanceInfo guidance;
}

[System.Serializable]
public class WeatherInfo { public string type; public float intensity; }
[System.Serializable]
public class BreathInfo { public string phase; public float rate; }
[System.Serializable]
public class GuidanceInfo { public string prompt; public float circle_radius; }

public class WeatherController : MonoBehaviour
{
    [Header("Particle Systems")]
    public ParticleSystem rainParticles;
    public ParticleSystem lightningParticles;
    public ParticleSystem heatParticles;
    public ParticleSystem snowParticles;
    public ParticleSystem fogParticles;
    public ParticleSystem colorSparkles;

    [Header("Background")]
    public SpriteRenderer backgroundRenderer;

    [Header("Weather Colors")]
    public Color stormColor = new Color(0.18f, 0.18f, 0.23f);
    public Color heatColor = new Color(0.8f, 0.27f, 0.0f);
    public Color snowColor = new Color(0.69f, 0.72f, 0.75f);
    public Color fadeGray = new Color(0.6f, 0.6f, 0.6f);
    public Color clearColor = new Color(0.4f, 0.7f, 1.0f);

    private string currentWeatherType;
    private float currentIntensity = 0f;

    public void ApplyData(SRPData data)
    {
        if (data?.weather == null) return;

        SwitchWeather(data.weather.type);
        currentIntensity = data.weather.intensity;

        UpdateBackground(data.weather.type, data.weather.intensity);
        UpdateParticles(data.weather.type, data.weather.intensity);
    }

    void SwitchWeather(string type)
    {
        if (type == currentWeatherType) return;
        currentWeatherType = type;

        // 全部先关闭
        if (rainParticles) rainParticles.gameObject.SetActive(false);
        if (lightningParticles) lightningParticles.gameObject.SetActive(false);
        if (heatParticles) heatParticles.gameObject.SetActive(false);
        if (snowParticles) snowParticles.gameObject.SetActive(false);
        if (fogParticles) fogParticles.gameObject.SetActive(false);
        if (colorSparkles) colorSparkles.gameObject.SetActive(false);

        // 按类型开启
        switch (type)
        {
            case "storm":
                rainParticles?.gameObject.SetActive(true);
                lightningParticles?.gameObject.SetActive(true);
                break;
            case "heat":
                heatParticles?.gameObject.SetActive(true);
                break;
            case "snow":
                snowParticles?.gameObject.SetActive(true);
                fogParticles?.gameObject.SetActive(true);
                break;
            case "fade":
                colorSparkles?.gameObject.SetActive(true);
                break;
        }
    }

    void UpdateBackground(string type, float intensity)
    {
        if (!backgroundRenderer) return;

        Color weatherColor = type switch
        {
            "storm" => stormColor,
            "heat" => heatColor,
            "snow" => snowColor,
            "fade" => fadeGray,
            _ => clearColor
        };

        // intensity=1 → 全天气色; intensity=0 → 晴天
        Color targetColor = Color.Lerp(clearColor, weatherColor, intensity);
        backgroundRenderer.color = Color.Lerp(backgroundRenderer.color, targetColor, Time.deltaTime * 2f);

        // 褪色场景额外处理饱和度
        if (type == "fade")
        {
            float sat = 1f - intensity; // intensity=1 → sat=0 (全灰)
            // 通过材质属性或后处理调整饱和度
        }
    }

    void UpdateParticles(string type, float intensity)
    {
        var activePS = GetActiveParticles();
        if (!activePS) return;

        var emission = activePS.emission;
        emission.rateOverTime = intensity * 200f;

        var main = activePS.main;
        main.simulationSpeed = 0.5f + intensity * 1.5f;
    }

    ParticleSystem GetActiveParticles()
    {
        if (rainParticles && rainParticles.gameObject.activeSelf) return rainParticles;
        if (heatParticles && heatParticles.gameObject.activeSelf) return heatParticles;
        if (snowParticles && snowParticles.gameObject.activeSelf) return snowParticles;
        if (colorSparkles && colorSparkles.gameObject.activeSelf) return colorSparkles;
        return null;
    }
}
'''
  }]
)
```

### B6. 编辑 PromptDisplay.cs — 环境提示词浮现

```
script_apply_edits(
  script_path="Assets/Scripts/PromptDisplay.cs",
  edits=[{
    "edit_type": "replace",
    "target": "class_body",
    "new_code": '''
using UnityEngine;
using TMPro;

public class PromptDisplay : MonoBehaviour
{
    public TextMeshProUGUI promptText;
    public float fadeInDuration = 0.8f;
    public float holdDuration = 3.0f;
    public float fadeOutDuration = 1.2f;

    private float timer;
    private enum State { FadingIn, Holding, FadingOut, Idle }
    private State state = State.Idle;

    public void ShowPrompt(string text)
    {
        if (promptText) promptText.text = text;
        timer = 0f;
        state = State.FadingIn;
    }

    void Update()
    {
        switch (state)
        {
            case State.FadingIn:
                timer += Time.deltaTime;
                SetAlpha(Mathf.Clamp01(timer / fadeInDuration));
                if (timer >= fadeInDuration) { timer = 0f; state = State.Holding; }
                break;
            case State.Holding:
                timer += Time.deltaTime;
                if (timer >= holdDuration) { timer = 0f; state = State.FadingOut; }
                break;
            case State.FadingOut:
                timer += Time.deltaTime;
                SetAlpha(1f - Mathf.Clamp01(timer / fadeOutDuration));
                if (timer >= fadeOutDuration) { SetAlpha(0f); state = State.Idle; }
                break;
        }
    }

    void SetAlpha(float a)
    {
        if (!promptText) return;
        var c = promptText.color;
        c.a = a;
        promptText.color = c;
    }
}
'''
  }]
)
```

### B7. 在 StormScene 中组装

```
manage_scene(action="load", name="StormScene")

# 背景
manage_gameobject(action="create", name="Background", components=["SpriteRenderer"])
manage_components(action="modify", target="Background.SpriteRenderer", properties={"sortingOrder": -10})

# 呼吸引导圈（Spout 接收平面，Layer 1）
manage_gameobject(action="create", name="SpoutReceiverPlane", components=["MeshRenderer", "MeshFilter"])
manage_gameobject(action="modify", name="SpoutReceiverPlane", transform={"position": [0, -1, 0], "scale": [19.2, 10.8, 1]})
manage_components(action="add", target="SpoutReceiverPlane", component="SpoutReceiver")

# 旅人（占位矩形）
manage_gameobject(action="create", name="Traveler", components=["SpriteRenderer", "Animator"])
manage_gameobject(action="modify", name="Traveler", transform={"position": [-3, -2, 0]})

# 粒子系统
manage_gameobject(action="create", name="Particles_Rain", components=["ParticleSystem"])
manage_gameobject(action="create", name="Particles_Lightning", components=["ParticleSystem"])
manage_gameobject(action="create", name="Particles_Heat", components=["ParticleSystem"])
manage_gameobject(action="create", name="Particles_Snow", components=["ParticleSystem"])
manage_gameobject(action="create", name="Particles_Fog", components=["ParticleSystem"])
manage_gameobject(action="create", name="Particles_ColorSparkles", components=["ParticleSystem"])
# 除风暴粒子外全部默认关闭
manage_gameobject(action="modify", name="Particles_Heat", active=False)
manage_gameobject(action="modify", name="Particles_Snow", active=False)
manage_gameobject(action="modify", name="Particles_Fog", active=False)
manage_gameobject(action="modify", name="Particles_ColorSparkles", active=False)

# 提示词 Canvas
manage_gameobject(action="create", name="PromptCanvas", components=["Canvas", "CanvasScaler"])
manage_gameobject(action="create", name="PromptText", parent="PromptCanvas", components=["TextMeshProUGUI"])

# 挂载脚本
manage_components(action="add", target="MainCamera", component="UDPReceiver")
manage_components(action="add", target="MainCamera", component="WeatherController")
manage_components(action="add", target="PromptCanvas", component="PromptDisplay")

# 关联引用
manage_script(action="modify_property", target="MainCamera.WeatherController", property="rainParticles", value="Particles_Rain")
manage_script(action="modify_property", target="MainCamera.WeatherController", property="lightningParticles", value="Particles_Lightning")
manage_script(action="modify_property", target="MainCamera.WeatherController", property="heatParticles", value="Particles_Heat")
manage_script(action="modify_property", target="MainCamera.WeatherController", property="snowParticles", value="Particles_Snow")
manage_script(action="modify_property", target="MainCamera.WeatherController", property="fogParticles", value="Particles_Fog")
manage_script(action="modify_property", target="MainCamera.WeatherController", property="colorSparkles", value="Particles_ColorSparkles")
manage_script(action="modify_property", target="MainCamera.WeatherController", property="backgroundRenderer", value="Background.SpriteRenderer")
manage_script(action="modify_property", target="PromptCanvas.PromptDisplay", property="promptText", value="PromptText.TextMeshProUGUI")

manage_camera(action="apply_preset", preset="side_scroller")

manage_scene(action="save")
manage_scene(action="screenshot")
```

---

## 阶段 C：闭环验证

```
# 1. 启动 Python 模拟数据（风暴模式）
python main.py --simulated --weather storm --duration 0

# 2. TD 侧验证
get_td_nodes(parentPath="/project1/SRP")
get_td_node_parameters(path="/project1/SRP/UDP_Input/udp_in")
get_td_node_parameters(path="/project1/SRP/BreathGuide/spout_out")
# 应看到 port=5005, active=true, sender=SRP_BreathCircle

# 3. Unity 侧验证
manage_scene(action="load", name="StormScene")
manage_editor(action="enter_play_mode")
manage_scene(action="screenshot")  # 应看到暗灰色背景+呼吸圈纹理+雨滴
read_console()  # 应无报错，Spout receiver connected
manage_editor(action="exit_play_mode")
```

---

## 工作流速查卡

| # | 阶段 | 关键 MCP 工具 | 预计耗时 |
|---|------|-------------|:------:|
| A1 | 验证 TD 连接 | `get_td_info` | 1 min |
| A2 | 创建 TD 骨架（呼吸圈+Spout+监控台+曲线） | `execute_python_script` (1次) | 6 min |
| A3 | 验证 TD | `get_td_nodes` + `get_td_node_errors` | 2 min |
| B1 | 验证 Unity 连接 + 导入 KlakSpout | `manage_scene(get_hierarchy)` + Package Manager | 3 min |
| B2 | 创建场景+脚本 | `batch_execute` (1次) | 3 min |
| B3-6 | 写 C# 脚本 | `script_apply_edits` (5 scripts) | 25 min |
| B7 | 组装风暴场景（Spout接收平面+全天气粒子+提示词Canvas） | `manage_gameobject` + `manage_components` | 10 min |
| C | 闭环验证 | Python + TD Spout + Unity Play | 5 min |
| **总计** | | | **~54 min** |

TD 恢复呼吸圈渲染+Spout（+2min），Unity 改为 Spout 接收展示（替换 BreathCircle 渲染，+2min KlakSpout 导入）。
