# 项目缓存、重复文件与来源材料整理

日期：2026-10-22。范围：`D:/Agent/srp`，不提交或推送，不改变任务状态。

## 实际完成

- 完成项目文件占用扫描，约221,220个文件、19.30 GiB逻辑大小；该数包含Git、环境、稀疏模拟器文件，不等于卷上的实际占用。
- 对20个来源、背景、历史快照及旧演练目录执行NTFS LZX原位无损压缩；没有打包后删除原目录，也没有改变引用路径。
- 14,451个文件压缩前后逐文件SHA-256及文件集合完全一致，总逻辑字节保持4,150,056,810。
- Win32 `GetCompressedFileSizeW`汇总从4,150,056,810降至2,823,120,064字节，差额1,326,936,746字节，约1.24 GiB。按文件身份排除硬链接重复；此为文件存储口径，不是卷空闲量差值。
- 压缩完成且补充本轮说明之前，来源库、历史框架和归档目录无Git内容差异；随后仅新增本记录、来源库导航及工作日志。BigRun、mock、分析CMD、最终BigRun TOE和Unity核心工程入口均存在。未启动TD/Unity或执行真实实验。

主要压缩范围：`agent/references/`；`agent/archive/`下project、runtime、tools、root-migration、normalization-summary-inputs、delivery及local中的backups、worktree-evidence、td-manual-debug；`agent/local/artifacts/`下目录改造/设计基线快照、旧TD study-v6/backend-v7演练材料、ECTRI反编译源码。完整20项绝对路径见机器清单。

## 已确认候选，但没有删除

删除命令被执行策略拦截，未启动执行，没有删除任何文件。不以压缩完成代替缓存清理完成。

| 候选 | 逻辑大小 | 判断与条件 |
|---|---:|---|
| `D:/Agent/srp/agent/modules/unity/SRP-Weather-Visual/Library` | 2,910.76 MiB | Unity生成缓存；检查时没有Unity进程，Assets、Packages、ProjectSettings齐全。删除后须重新导入；工程实际版本6000.4.9f1，不能假定2022版可直接重建。 |
| 同工程obj及项目源码区域的Python/pytest缓存、空JADX缓存 | 合计约9.38 MiB | 118个缓存目标合计2,920.13 MiB，均没有Git跟踪文件；不包括Python环境、工作树或历史签收归档内缓存。 |
| `D:/Agent/srp/agent/local/tools/jadx-1.5.6/jadx.zip` | 69.28 MiB | ZIP内7个文件与已有解压文件逐项大小和SHA-256一致；仅安装包冗余，工具本体保留。 |
| `D:/Agent/srp/agent/local/tools/ffmpeg/9.0.1/ffmpeg-release-essentials.zip` | 106.10 MiB | ZIP内45个文件与已有解压文件逐项一致；工具本体保留。 |

以上120个目标合计约3.02 GiB逻辑候选量，不计入本轮已释放量。未删除uv-cache，避免未核对的旧运行环境依赖被破坏。

## 重复文献与过期材料

在来源库、历史项目/运行文档、人类项目概览范围内，按文件内容发现以下3组完全相同的PDF；并非全项目所有格式的完整去重结论。

1. `agent/references/01-research-proposal/JMIR_meta-analysis.pdf` 与 `agent/references/04-gamification-emotion/Internet-Based Behavioral Activation for Depression Systematic.pdf`。
2. `agent/references/04-gamification-emotion/Evaluating the Therapeutic Alliance With a Free-Text CBT Conversational Agent (Wysa) A Mixed-Methods Study.pdf` 与同目录 `Evaluating the Therapeutic Alliance With a Free-Text CBT Conversational Agent (Wysa) A Mixed-Methods_Sinha_.pdf`。
3. `agent/references/04-gamification-emotion/Suppression and expression as distinct emotion-regulation processes in daily interactions _Cameron2017.pdf` 与同目录 `Thefivefacto modelofpersonality and emotion regulation Ametaanalysis.pdf`。

这些重复文件保留并压缩。来源库已有身份/来源隔离门，尤其第3组不能仅凭文件名当成两篇独立研究；需核验PDF题名、DOI和引用消费者后再决定唯一规范文件，不静默改写pdf_inventory或历史引用。

已退役的旅人/旧接口框架仍归于 `agent/archive/project/`，旧Mock/Spout说明归于 `agent/archive/runtime/`，已有历史标识，不作为当前入口；本轮压缩保留，不按日期删除历史依据。任务输入快照、签收原件、旧工作树差异和验收包也不作为重复垃圾处理。

## 保留与证据

未处理：`.git/`、Python/软件环境、`agent/archive/local/env/`、工作树、模拟器AVD及APK、真实BigRun原始记录、蓝牙驱动回滚材料、正式交付物与Unity资产/配置。未重编码PDF、图片或录屏。

本机完整记录：`D:/Agent/srp/agent/local/artifacts/project-cleanup-20261022/`。`plan.json`含候选和重复分组；`content-before.json`保存压缩前内容校验；`compression-result.json`及`compact.log`保存实际结果。该目录被现有规则忽略，不上传来源材料或本地日志。

本轮是本地存储压缩，Git文件内容及GitHub仓库体积不会因此缩小；缓存删除和文献身份归一化仍未关闭。

## 2026-10-30 有界收尾

按本次明确授权，未重扫全仓，复用原候选清单并定点核查旧TD模拟和ECTRI诊断。44份TD轨迹与511份P-02元数据、6份诊断/动作记录已归入 `agent/archive/local/cold-records-20261030/` 两个ZIP，561成员全部可读，内部路径保留。冷原件逻辑1,371,161,670字节；原位压缩后的存储口径470,748,301字节，ZIP合计423,471,174字节，不按逻辑大小冒充压缩新增收益。

50个被替代记录与6个已确认可再生/冗余目标同卷移至 `D:/_Codex待人工删除/srp/20261030-storage-closeout/`，合计4,607,381,275字节逻辑大小（约4.29 GiB），清单在该目录manifest.json；没有永久删除、覆盖或锁定失败。隔离实际释放0，当前因新增归档暂增约404 MiB占用，最终删除由用户执行。Unity再次开发需同版本重新导入Library，未在本轮启动编辑器或下载。

保留源码、人工作品、当前TOE/入口、环境与lock、正式包/注册状态、必要正负结果、真实BigRun记录、参与者和同意/匿名材料；AVD应用状态、uv缓存及身份待核对的重复PDF原地保留，未确认可替代不动。空间习惯已写入项目AGENTS，无新实验/API/发布/推送。
