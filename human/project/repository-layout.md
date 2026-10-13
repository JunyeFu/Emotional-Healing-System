# 仓库目录与命名规范

2026-10-13统一本地项目自有目录。逐文件位置及改动记录见[目录清单](https://github.com/JunyeFu/Emotional-Healing-System/blob/d2245d4dee7916f898be2ff872a2062b6617ee92/agent/repository-layout.json)。本轮范围覆盖已跟踪文件、未跟踪开发文件及随其所在目录移动的本地工程文件。

## 文件归属

| 位置 | 文件职责 |
|---|---|
| `human/project/` | 项目介绍、模块地图、目录规范 |
| `human/tasks/<任务编号>/` | 任务审阅文档及生成PDF |
| `human/assets/` | 项目展示图、预览和页面设计 |
| `human/deliverables/` | 给使用者的制品和交付入口 |
| `human/templates/` | 人类审阅模板 |
| `agent/modules/` | 可开发源码、原生工程及模块测试 |
| `agent/tasks/<任务编号>/` | inputs、execution、outputs、evidence、archive五类任务材料 |
| `agent/design/` | 当前设计源和版本化设计基线 |
| `agent/governance/` | planning、charter、boards、progress、risks、quality |
| `agent/tools/` | 现有生成器和项目维护工具 |
| `agent/runtime/` | 启动、环境和运行入口说明 |
| `agent/validation/` | 跨模块验证与受控实验材料 |
| `agent/references/` | 文献及来源材料 |
| `agent/work/` | 日期化工作记录 |
| `agent/archive/` | 保留原件的历史材料 |
| `agent/local/` | 本机工具、环境、工作树及临时产物 |

## 命名

- 项目自有业务目录采用小写语义英文和连字符，如`signal-processing`、`data-governance`。目录编号不承担模块身份；模块身份由模块地图维护。
- Python可导入包及模块采用snake_case；保留`srp_session_core`等现有导入名。
- 每个主要目录的说明入口使用`README.md`；中文正式文档保留清楚的中文标题，日期使用`YYYY-MM-DD`，既有版本标识保留。
- 任务目录使用注册表中的原任务编号；其标准子目录和`TASK.md`固定。
- Unity的Assets、Packages、ProjectSettings、GUID及资产名称，TD的工程内部名称，以及第三方源码、签收原件、领取快照按原有契约命名。全仓规范允许这些固定名称，不逐字翻译它们。
- 日期化规划包及编号章节保留正式文件身份，归入`planning/`；归档、证据和冻结输入保留原始内容。旧记录中的路径通过迁移清单及既有来源解析器查找。

## 迁移影响

本轮实际迁移16个业务目录，统一源码、治理和天气设计入口，同时调整当前脚本、文档和配置引用。工程内部层级保持原有深度。已有领取快照的字节及身份保留，来源解析器将原路径解析到新位置或原输入快照。

使用`agent/repository-layout.json`查询某个文件的旧位置、新位置和类别。该清单描述本轮迁移时的文件集合；新文件直接按上表归位。GitHub旧提交链接仍指向原提交中的原路径。

本规范随本地源码维护。前一份[目录改造任务书](repository-restructure-taskbook-20261013.md)中的有限归位范围已由本次全仓目录规范化要求扩展，展示首页和新人上手仍按该任务书完善。

## 本轮验证

6812个登记文件位置核对通过，16个业务目录迁移涉及1745个文件，545个当前消费者更新。910个当前Markdown链接、71包审阅文档及来源、5包88份冻结输入均通过对应检查。模块回归715通过、2个原有失败；60包执行测试838通过、32个原有失败，与迁移前c27ca0d6对照无新增失败。

任务编号、原生工程内部身份及原件按上述规则保留；真实Unity/TD编辑器启动尚未在本轮复验。详细结果见[验证记录](https://github.com/JunyeFu/Emotional-Healing-System/blob/d2245d4dee7916f898be2ff872a2062b6617ee92/agent/work/codex-verification-log.md)。
