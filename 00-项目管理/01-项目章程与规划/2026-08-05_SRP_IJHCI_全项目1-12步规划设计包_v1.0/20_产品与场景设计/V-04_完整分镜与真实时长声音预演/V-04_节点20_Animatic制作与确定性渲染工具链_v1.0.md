# V-04 节点20：Animatic制作与确定性渲染工具链

> 状态：ACCEPTED
> 日期：2026-08-24
> 当前边界：工具链设计已冻结；FFmpeg尚未安装，实际预演制品尚未生成。

## 1. 当前环境事实

| 工具 | 版本或状态 |
|---|---|
| Python | `3.14.4` |
| Pillow | `12.2.0` |
| NumPy | `2.4.6` |
| Unity | `6000.4.9f1` |
| TouchDesigner | `2025.32820` |
| FFmpeg/ffprobe | 未安装 |
| Krita/GIMP/ImageMagick/Blender | 未安装 |

V-04不使用Unity或TouchDesigner作为制作权威，以免把分镜预演与后续运行实现混为同一证据层。

## 2. 冻结工具链

| 工具 | 冻结版本 | 职责 |
|---|---:|---|
| Python | `3.14.4` | 读取Schema、轨迹、节拍和资产清单，生成渲染计划 |
| Pillow | `12.2.0` | PNG、遮罩、提示层和分镜格处理 |
| NumPy | `2.4.6` | 像素差异掩码、轨迹插值和画面检查 |
| FFmpeg/ffprobe | `9.0.1` | 视频合成、恒定帧率编码、声音装配和媒体检查 |

FFmpeg来源以[FFmpeg官方下载页](https://ffmpeg.org/download.html)为版本入口，Windows侧采用该页链接的[gyan.dev release essentials 9.0.1](https://www.gyan.dev/ffmpeg/builds/)。

## 3. 安装与许可边界

候选安装位置：

```text
D:\Agent\03-SRP\.tools\ffmpeg\9.0.1\
```

- `.tools/`加入`.gitignore`，不提交FFmpeg二进制。
- 不调用系统PATH中的未知FFmpeg；渲染脚本只读取工具锁中的绝对路径。
- 下载包SHA-256、解压后可执行文件哈希、版本输出和来源URL进入工具锁。
- FFmpeg只作为V-04制作工具，不进入Unity制品。
- gyan.dev静态构建按其页面标记为GPLv3并进入G-02工具与许可台账。
- 具体二进制许可状态必须依据构建配置记录，不只根据FFmpeg名称推断；参考[FFmpeg许可说明](https://ffmpeg.org/legal.html)。

跟踪文件`V-04_toolchain-lock_v1.0.json`至少记录：

```json
{
  "python": "3.14.4",
  "pillow": "12.2.0",
  "numpy": "2.4.6",
  "ffmpeg": "9.0.1",
  "ffmpeg_distribution": "gyan_release_essentials",
  "archive_sha256": "<sha256>",
  "ffmpeg_exe_sha256": "<sha256>",
  "ffprobe_exe_sha256": "<sha256>",
  "license_status": "REGISTERED_DEVELOPMENT_TOOL_ONLY"
}
```

## 4. 资产源格式

每个天气使用以下分层源：

```text
sky/
far/
mid/
near/
target_scene_native/
actual_scene_native/
recovery_masks/
transition_masks/
```

- 普通图层使用RGBA PNG、8-bit、sRGB。
- 累计环境和渐变遮罩使用16-bit灰度PNG。
- 公共画布为`1920×1080`。
- 长卷轴原始段不超过`3840×1080`，相邻段重叠`192–288 px`。
- 通过组合清单形成不少于`6.75`屏宽的有效覆盖，不把约12960像素长图作为唯一编辑权威。
- 所有临时图层标记`TEMP_REFERENCE_ONLY`。
- 所有AI生成、拆层和补绘输入记录提示词、参考输入、模型、日期和哈希。

## 5. 渲染架构

采用三层渲染：

```text
共享环境层
+ 条件目标与实际提示层
+ 外部评审层
```

共享环境层包含天气背景、视差卷轴、累计环境、山雾长廊、转场和天气声音，只渲染一次并由两条件复用。条件提示层分别生成`scene_native_target_actual`和`abstract_pacer_target_actual`透明结果，只读取同一预演轨迹。外部评审层只用于`3840×1200`评审制品，不进入参与者视图。

## 6. Python与FFmpeg职责

Python负责：

1. 校验工具锁和源文件哈希。
2. 读取五十条节拍和确定性设计预演轨迹。
3. 计算每帧状态但不改写事件时间。
4. 生成结构化FFmpeg filtergraph。
5. 生成提示关键帧、透明遮罩和评审信息层。
6. 运行FFmpeg并收集退出码。
7. 使用ffprobe验证输出。
8. 生成输出清单和验证报告。

FFmpeg负责分段卷轴裁切、视差、透明层合成、交叉淡化、48 kHz声音混合、CFR编码和媒体封装。制作链不生成完整24300张PNG中间帧。

## 7. 视频编码规格

参与者视图：

```text
container=MP4
video=H.264
pixel_format=yuv420p
resolution=1920x1080
frame_rate=30 fps CFR
core_frames=24000
quality=CRF 18
audio=AAC 48 kHz stereo 320 kbps
```

静音版不包含音频流。双条件评审视图为`3840×1200`、`30 fps CFR`、`yuv420p`，只保留一条共享48 kHz立体声音轨。所有编码参数写入生成清单，不依赖默认值。

## 8. 确定性边界

- JSON事件和时间戳是权威，FFmpeg帧号不是。
- 每个视频帧读取该帧时点之前最近的有效状态。
- 不跨步骤平滑，不为视频对齐移动事件。
- 同一源、工具锁和配置必须生成相同帧数、事件映射和关键帧像素。
- 压缩容器哈希允许受编码实现影响，验收同时保存关键帧解码像素哈希。
- 两条件掩码外像素必须一致，声音源时间、增益和淡化包络必须一致。

## 9. 渐进渲染过程

1. 生成10秒单天气技术烟雾测试。
2. 生成25秒完整`demo`测试。
3. 生成200秒单天气模块测试。
4. 生成两条件同模块并列检查。
5. 生成800秒核心参考顺序测试。
6. 加入首尾示意保持。
7. 生成四条参与者视图。
8. 生成双条件评审视图。
9. 生成失败状态评审卷。
10. 执行媒体、帧、声音和差异掩码验收。

每一级通过后才进入下一级。

## 10. 失败关闭规则

出现以下任一情况停止：

```text
FFmpeg版本不符
工具哈希不符
使用未知PATH工具
Schema校验失败
轨迹哈希漂移
资产未登记
磁盘空间不足
帧率不是CFR
核心帧数不是24000
两条件共享状态漂移
声音轨迹漂移
条件差异越过掩码
输出包含参与者可见技术文字
```

不得静默降低分辨率、帧率、声音规格或跳过天气模块。

## 11. 不承担项

该工具链不证明Unity场景已经实现、正式运行帧率已经冻结、正式构建已经完成、临时图像或声音已经获得正式使用资格、正式输入链已经接入或TouchDesigner联合运行已经完成。

## 12. 验收条件

1. 工具锁包含所有版本、来源和哈希。
2. FFmpeg只从冻结绝对路径调用。
3. 10秒、25秒、200秒和完整预演逐级通过。
4. 所有输出由同一分镜源和轨迹生成。
5. 参与者视图符合`1920×1080、30 fps CFR`。
6. 评审视图符合`3840×1200、30 fps CFR`。
7. 800秒核心区恰好24000帧。
8. 带声版只有一条48 kHz立体声音轨，静音版不存在音频流。
9. 两条件掩码外像素一致。
10. 关键帧像素哈希和媒体检查结果进入生成清单。
11. FFmpeg及全部临时资产进入G-02台账。
12. FFmpeg二进制和大型中间文件不进入Git。
13. 自动验证结果仍只构成V-04预演证据。
