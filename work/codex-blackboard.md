# Codex Blackboard

> Purpose: lightweight project-local working memory for the current task. Keep this file factual, brief, and easy to reset.

## Current Task Goal

保存截至 2026-08-04 的 Grill 连续访谈上下文，记录用户原始问题脉络、可复核判断依据、方案版本变化、已确认约束、待确认建议和下一道追问，并在项目管理入口建立稳定导航。

## Constraints

- 不修改全局 Codex 配置。
- 不安装 hooks。
- 不写入长期 memory。
- 不覆盖已有项目规则。
- 本次不移动或删除 Unity、TD、实验材料、参考文献及用户未跟踪文件。
- 已有 4 个删除项、`CLAUDE.md` 修改、`SRP/` 和根目录 docx 均视为用户改动。
- 保留 SRP 术语边界，避免新增禁用表达。
- 不导出内部隐式推理；以“观察—判断—影响”记录可审计依据。
- 完成后验证文件存在、入口引用有效、术语扫描和 `git diff --check` 通过。

## Known Evidence

- Git 根目录为 `D:/Agent/03-SRP`，任务开始时 HEAD 为 `ff60db4`，分支为 `main`。
- `PROJECT_MODULES.md` 仍把 TD Spout 作为 Unity 输入；后续访谈已确认 Unity 必须脱离 TD 独立完成体验，因此模块地图需要在主线确认后另行修订。
- 旧科研确认稿仍记录每场景 7 分钟、8-12 人等早期方案；当前访谈已将场景约束改为 90-120 秒，并提出 `4×4` 平衡设计。
- 上一轮 Grill 暂停在是否把论文核心改为“场景—呼吸匹配额外收益”的确认问题。

## Risks

- 访谈中的早期意见和后期决定可能冲突，记录必须显式区分状态，不能覆盖历史。
- 用户已有删除项可能属于进行中的材料调整，不得恢复或提交。
- 本任务只记录上下文，不应把建议待确认项误写成已批准需求。

## Next-Step Queue

1. 新增日期化 Grill 访谈总结与决策演化记录。
2. 在 M00 项目管理入口增加稳定导航。
3. 验证记录完整性、链接、术语和 diff 格式。
4. 仅暂存本任务文件，提交并推送。
