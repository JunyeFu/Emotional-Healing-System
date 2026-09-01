# V-04 执行上下文

## 当前权威

| 范围 | 文件 |
|---|---|
| 实施裁定 | `V-04_科研便捷实施裁定_v1.2.md` |
| 当前状态 | `V-04_实施状态与H1确认记录_v2.6.md` |
| 四天气固定镜头修订 | `V-04_H3_四天气固定镜头修订合同_v1.0.md` |
| R2大景深事件构图 | `V-04_H3_四天气大景深事件构图合同_v1.0.md` |
| R2独立背景预览与选择 | `V-04_H3_R2大景深AAA背景生图提示词_v1.0.md`、`V-04_H3_R2大景深背景预览候选清单_v1.0.json`、`V-04_H3_R2背景选择记录_v1.0.json`、`V-04_H3_R2背景选择验证记录_v1.0.md`、`V-04_H3_R2大景深背景预览验证记录_v1.0.md`、`validate_v04_h3_r2_previews.py` |
| 可拆层背景重建候选 | `V-04_H3_可拆层背景重建合同_v1.0.md`、`V-04_H3_可拆层背景重建候选清单_v1.0.json`、`V-04_H3_fade_v4真实感重建提示词_v1.0.md`、`V-04_H3_fade_v5选定版提示词与来源记录_v1.0.md`、`validate_v04_h3_layerable_background_rebuild.py` |
| 历史固定镜头四联预览 | `V-04_H3_固定镜头高精度背景生图提示词_v1.0.md`、`V-04_H3_固定镜头背景预览候选清单_v1.0.json` |
| 固定镜头预览验证 | `V-04_H3_固定镜头背景预览验证记录_v1.0.md` |
| H1选择 | `V-04_H1选择记录_v1.0.json` |
| H2当前设计合同 | `V-04_H2_candidate-v11_固定底片样片合同_v1.0.md` |
| H2当前配置与清单 | `V-04_H2样片配置_v1.4.json`、`V-04_H2候选清单_v1.4.json` |
| H2当前评审 | `V-04_H2样片评审说明_v1.5.md` |
| H2人工结论 | `V-04_H2人工评审结论_v1.0.md`、`V-04_H2人工评审记录_v1.0.json` |
| H3 storm输入 | `V-04_H3_storm核心机制样片合同_v1.0.md`、`V-04_H3_storm样片配置_v1.0.json`、`V-04_H3_storm候选清单_v1.0.json` |
| H3 storm验收 | `V-04_H3_storm机器验收记录_v1.0.json`、`V-04_H3_storm样片评审说明_v1.1.md`、`V-04_H3_storm人工评审结论_v1.0.md`、`V-04_H3_storm人工评审记录_v1.0.json`、`validate_v04_h3_storm.py` |
| H3 heat输入 | `V-04_H3_heat核心机制样片合同_v1.0.md`、`V-04_H3_heat样片配置_v1.0.json`、`V-04_H3_heat候选清单_v1.0.json` |
| H3 heat验收 | `V-04_H3_heat机器验收记录_v1.0.json`、`V-04_H3_heat样片评审说明_v1.0.md`、`validate_v04_h3_heat.py` |
| H3 snow输入 | `V-04_H3_snow核心机制样片合同_v1.0.md`、`V-04_H3_snow样片配置_v1.0.json`、`V-04_H3_snow候选清单_v1.0.json` |
| H3 snow验收 | `V-04_H3_snow机器验收记录_v1.0.json`、`V-04_H3_snow样片评审说明_v1.0.md`、`validate_v04_h3_snow.py` |
| H3 corridor输入 | `V-04_H3_corridor通用转场样片合同_v1.0.md`、`V-04_H3_corridor样片配置_v1.0.json`、`V-04_H3_corridor候选清单_v1.0.json` |
| H3 corridor验收 | `V-04_H3_corridor机器验收记录_v1.0.json`、`V-04_H3_corridor样片评审说明_v1.0.md`、`validate_v04_h3_corridor.py` |
| H3合并合同与配置 | `V-04_H3合并评审与Unity交接合同_v1.0.md`、`V-04_H3合并评审配置_v1.0.json` |
| H3六节点交接 | `V-04_H3_四天气六节点Unity交接分镜_v1.0.json`、`V-04_H3_四天气六节点Unity交接分镜_v1.0.md`、`V-04_H3_Unity交接清单_v1.0.md` |
| H3合并证据 | `V-04_H3合并评审候选清单_v1.0.json`、`V-04_H3合并评审机器验收记录_v1.0.json`、`V-04_H3合并评审独立Agent复核记录_v1.0.md`、`V-04_H3合并评审说明_v1.0.md` |
| H2当前验证器 | `validate_v04_h2_v11.py` |
| H2背景签收 | `V-04_H2固定底片选择记录_v1.0.json`、`V-04_H3_fade_v5选定版提示词与来源记录_v1.0.md` |
| H2独立视觉预审 | `V-04_H2_candidate-v9_独立视觉预审报告_v1.0.md` |
| H2历史机器证据 | candidate-v8的v1.1配置/清单/评审；candidate-v9的v1.2配置/清单/评审、渲染器、校验器和独立预审 |

冲突时，任务范围、fade镜头、原生背景和当前H2路径以科研便捷实施裁定v1.2及candidate-v11合同为准；candidate-v11复用candidate-v10已确认机制，色潮、实际色迹和整屏复色语义继续沿用candidate-v9合同。已删除的v1.0长预演、节点18-25和ADR只存在于Git历史，不是当前执行输入。

## 任务边界

V-04负责在Unity制作前冻结四个天气的核心视觉机制、两种呼吸提示组织、模块内关键节点和通用转场。V-04不实现完整Unity体验，不修改F-01协议，不生成正式研究运行证据。

保留两种提示条件：

- `scene_native`：目标由场景内自然机制表达，实际由近景响应元素表达。
- `abstract_pacer`：外环表达目标，内环表达实际。

两条件共享场景、天气、固定相机、整屏颜色曲线、累计环境、声音、时长和输入。fade不再横向滚动；条件差异只允许存在于目标与实际提示的可见组织。

## 当前硬门

| 硬门 | 状态 | 说明 |
|---|---|---|
| H1风格锚点 | `PASS` | `storm-A/heat-A/snow-B/fade-B/corridor-A` |
| H2 candidate-v8机器门 | `PASS_HISTORICAL_EVIDENCE` | 10秒、300帧、两条件整屏复色，提示区外差异为0 |
| H2 candidate-v8人工设计 | `REVISE` | 原生提示具有矩形区、通道图和悬浮线观感，未自然承载循环叹息 |
| H2 candidate-v9机器门 | `PASS` | 300帧双条件媒体、整屏复色、水面裁切、三步骤几何、实际步骤忠实度、灰度提示和条件一致性通过 |
| H2 candidate-v9独立视觉预审 | `READY_FOR_TEAM_DIRECTOR_REVIEW` | 第一轮线性实际提示被退回；修正版改为水面断续反光，九项预审无阻断项 |
| H2 candidate-v9团队总监 | `REVISE` | 横向滚动不利于观察固定水系；原生底图恢复后仍灰暗压抑 |
| H2 candidate-v10背景 | `PASS` | 团队总监已确认固定镜头全彩湿地背景 |
| H2 candidate-v10机器门 | `PASS` | 300帧固定镜头媒体、整屏复色、水体裁切、三步骤、实际忠实度、条件一致性、媒体健康和声音通过 |
| H2 candidate-v10团队总监 | `PASS` | 团队总监确认fade通过；按v1.4规则记录包含`native_naturalness`在内的九项均为`PASS` |
| H2 candidate-v11底片 | `PASS` | 团队总监已选择`fade v5`固定镜头底片 |
| H2 candidate-v11机器门 | `PASS` | 300帧固定镜头媒体、整屏复色、水体裁切、三步骤、实际忠实度、条件一致性、媒体健康和声音通过 |
| H2 candidate-v11团队总监 | `PENDING_HUMAN_CONFIRMATION` | 等待按v1.5评审说明完成九项观看判断 |
| H3 storm输入 | `PASS_HUMAN` | 12秒双条件雨幕风门样片已通过机器门、视觉预检和团队总监人工确认 |
| H3 heat输入 | `PASS_MACHINE` | 10秒双条件冷流风道样片已通过机器门和Codex视觉预检 |
| H3 snow输入 | `PASS_MACHINE` | 10秒双条件粉雪升沉样片已通过机器门和Codex视觉预检 |
| H3 corridor输入 | `PASS_MACHINE` | 12秒通用山雾长廊转场已通过机器门和Codex视觉预检；两条件逐帧相同 |
| H3输入门 | `PASS` | fade、storm、heat、snow与corridor五项输入齐备 |
| H3合并机器门 | `PASS` | 62秒合并视频、五项源门、四天气24节点、F-01/F-05语义、精确输出路径和资产边界通过 |
| H3独立复审 | `PASS` | 第一轮问题已按P1至P3修复；第二轮无未关闭P1-P3 |
| H3旧合并候选 | `SUPERSEDED` | 机器门与独立复审结果保留；三天气由滚动改为固定镜头后，不再进入原团队总监确认 |
| H3固定背景选择 | `PASS` | 团队总监已确认`storm=B, heat=C, snow=C, fade=C` |
| H3可拆层背景重建 | `CANDIDATE_READY_FOR_HUMAN_REVIEW` | 四张构图基准图与分层合同已生成；待团队总监确认后导出实际透明分层文件 |

candidate-v8和v9媒体继续位于各自Git忽略目录并作为历史证据。candidate-v10媒体位于`.artifacts-local/V-04/H2/candidate-v10/`；candidate-v11媒体位于`.artifacts-local/V-04/H2/candidate-v11/`。Git保存对应配置、清单、彩色/灰度关键帧、渲染器和验证器。

## candidate-v10摘要

- fade采用固定镜头和固定水系；两条件不再横向卷动。
- 原生背景为明亮但克制的全彩雨后湿地，完全褪色由运行时产生。
- 主水道、左侧支流汇入口和右下下游出口保持可见，为后续三步骤色潮和近景实际色迹提供稳定坐标。
- candidate-v9的目标、实际、累计与背景职责分离继续有效；candidate-v10已经完成固定镜头双条件渲染并通过机器门。

## candidate-v11摘要

- 使用团队总监选择的`fade v5`固定镜头底片；
- 时间、整屏复色、色潮、实际色迹、抽象双环和声音与candidate-v10一致；
- v11专项机器门已通过，当前只等待九项人工评审。

## 下一步

团队总监先审阅candidate-v11固定底片双条件样片。通过后继续`H3_LAYERABLE_BACKGROUND_REBUILD`，确认其余构图并导出实际透明分层文件；此前V-04继续保持`IN_PROGRESS`且不解锁V-05。
