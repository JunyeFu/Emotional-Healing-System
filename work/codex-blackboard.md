# Codex Blackboard

> Purpose: lightweight project-local working memory for the current task. Keep this file factual, brief, and easy to reset.

## Current Task Goal

重新盘点 D 盘 SRP 项目，以模块职责、接口、依赖和验证入口整理全项目导航；修正迁移后旧路径与失效入口，保持已有用户工作区改动不变，并在验证后提交推送。

## Constraints

- 不修改全局 Codex 配置。
- 不安装 hooks。
- 不写入长期 memory。
- 不覆盖已有项目规则。
- 本次不移动或删除 Unity、TD、参考文献及用户未跟踪文件。
- 已有 4 个删除项、`CLAUDE.md` 修改、`SRP/` 和根目录 docx 均视为用户改动。
- 保留 SRP 术语边界，避免新增禁用表达。
- 完成后验证文件存在、入口引用有效、`git diff --check` 通过。

## Known Evidence

- Git 根目录为 `D:/Agent/03-SRP`，任务开始时 HEAD 为 `39536558067aa15dd536f00b43c087371b95c22d`。
- 研发目录约 2.7 GB，但受版本控制的研发文件约 484 个；Unity 生成目录不属于项目模块。
- `README_run.md` 与 SE 方案仍包含旧 C 盘路径。
- 根目录未跟踪 docx 与 `00-项目管理/项目规约/SRP项目规划书_李俊扬组.docx` 哈希相同，本次保留。
- 现有入口引用了用户已删除的验证文档，需要改为稳定的模块入口。

## Risks

- 物理移动 Unity/TD 文件会破坏工程引用，因此本次只整理导航和模块接口。
- 用户已有删除项可能属于进行中的材料调整，不得恢复或提交。
- Python 自动测试不能替代 TD、Spout 和 Unity 的人工闭环复核。

## Next-Step Queue

1. 已完成模块地图和一级目录入口。
2. 已修正 D 盘运行路径及失效链接。
3. 已通过 42 项 Python 测试、链接扫描、术语扫描和 `git diff --check`。
4. 仅暂存本任务文件，提交并推送。
