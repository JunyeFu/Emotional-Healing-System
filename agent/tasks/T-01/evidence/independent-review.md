# T-01 本轮独立复核

日期：2026-09-28。复核对象：D:\Agent\srp 当前工作区中的规范化与可读性修复，不是历史候选重新签收。

## 结论与缺陷

当前可读候选、五张截图和链路状态相符；历史制品未被本轮候选覆盖，未发现沿用历史真人签名或宣称 A 主题、真实设备已完成。发现 **2 项 P2 验证器缺陷、1 项 P3 文档缺陷**；未发现 P0/P1。两个 P2 均已用实际代码的 AST 片段在内存中复现，不是当前 TOE 已发生功能漂移的判断。

### [P2] 核心内容比较漏掉当前 TOE 新增文件

位置：[verify.py:75](D:/Agent/srp/agent/tasks/T-01/execution/verify.py:75)，相关逻辑为 75–92 行。

`core` 仅从历史目录清单生成，后续循环只检查这些旧文件是否缺失或变化，没有反向检查当前核心目录新增项。新增 DAT/节点等功能内容仍可能得到空的 `functional_differences`，使“当前工程只有编辑器布局变化”的校验错误通过。

复现：读取现有 signed/current 展开目录，在内存中的 `current_entries` 增加 `project1/T01_TelemetryPanel/Runtime/unverified_send.text`，执行原比较循环，输出 `core_differences=[]`。未写文件或修改 TOE。

最小修正：先比较历史与当前核心条目集合，将新增项与删除项一并列为功能差异，再执行现有逐文件比较。本次独立复核额外检查了双向集合，当前实际集合相等，49 项内部文件、13 项编辑器布局差异确实成立。

### [P2] LFS 分支没有验证指针与物化制品的对应关系

位置：[verify.py:46](D:/Agent/srp/agent/tasks/T-01/execution/verify.py:46)，相关逻辑为 42–49 行。

当前分支只识别 LFS 版本头，随后直接标记 `lfs_pointer_vs_materialized_artifact`。此前对物化字节的历史清单校验不能替代对 Git 指针自身 `oid sha256:` 和 `size` 的核对；指针指向另一对象时仍会被接受，不能证明该物化制品来自指定 Git 候选。

复现：执行原 LFS 判断 AST 片段，输入 OID 为 64 个零、size 为 999999 的指针以及 `b'different artifact'`，没有拒绝，仍输出上述 LFS policy。

最小修正：解析指针 OID/size，与已经选定的物化字节哈希及长度比较，不符就拒绝。本次 23 件实际比较中为 13 件 raw bytes、10 件 Git 换行差异，**没有触发 LFS 指针分支**；因此此缺陷不推翻本次实际历史制品核对结果，也不能把本轮测试写成已实测 LFS 分支。

### [P3] A 主题实施记录仍链接到已移除的旧脚本

位置：[workbench-a-implementation.md:8](D:/Agent/srp/02-技术研发/03-TouchDesigner/t01_telemetry_panel/design/workbench-a-implementation.md:8)。

`[build_workbench_a.py](../build_workbench_a.py)` 解析到已删除的模块入口，点击不能打开构建器。第 19 行 Textport 命令已正确改为 Agent execution 路径，但第 8 行链接尚未同步。

最小修正：只将该链接指向 `../../../../agent/tasks/T-01/execution/build_workbench_a.py`。

## 检查范围与结果

- 首条命令为 `git status --short`：10 个已跟踪路径有修改/删除，`agent/tasks/T-01/` 为未跟踪目录。按当前工作区审查，没有将未提交内容当作已发布版本。
- 检查 execution 中全部 8 个 Python 文件、verify.ps1、执行说明、TASK、当前交接合同及当时已有的 summary.json；检查模块 README、A 主题实施记录、两份 T-01 测试源及 F-04 测试中的写入边界。未扫描无关目录、未联网。
- 路径：TASK/ROOT/MODULE 和 replay 的 `parents[4]` 均定位到当前仓库；两份迁移测试引用新 execution 路径。旧模块脚本已删除，清理脚本仅归档，归档内容与 Git 原文仅有 LF/CRLF 区别。上面的 P3 为发现的失效链接。
- 输出：builder 的新 TOE/TOX、host/TD 证据及新清单均指向任务包 `evidence/runtime`；探针只复制源 TOE 到时间戳 scratch 后注入回调；repair 和 A 主题候选拒绝覆盖已有候选。重复探针会替换本轮 runtime 的固定截图/状态，并非历史模块证据；未把这种本轮可刷新输出误判为覆盖历史签收制品。
- 历史制品：只读重新读取指定 Git 候选与原清单，23 件长度/哈希及 artifact_comparison 的当前哈希一致。TOX 和历史证据保持原清单身份；模块当前 TOE 为 `3A4DB364691D8A6AFFF10284AB5DF59060AD18D96BE2ADF369774F04643536ED`，与历史 TOE 不同。
- 当前 TOE：复用已有 `identity/20260928-191159` 展开文件，先核对 signed/current TOE 哈希，再双向核对核心目录集合。49 项核心文件相等，13 项 `.n` 差异仅涉及现有比较规则允许的 tile、viewport、current 选择标识；其余核心内容一致。已有 cleanup 报告显示六个默认演示节点已移除、display_out 绑定成立。
- 可读候选：哈希为 `B03DC5685A2910D7E110D990E7C3B361DC28A0B312985D0E8712C2DDC67B939E`。核对已有 layout 展开文件，只变化 panel_text、resp_sqi_bar、ecg_sqi_bar、stream_badge 四个参数文件，参数与 layout_repair.json 相符。18px 字体、20px 位置边距、6px 行距与 builder 一致；SQI 条及状态徽标位置/尺寸也与 builder 一致。
- 探针身份：源哈希与可读候选相等；实际 scratch probe 哈希为 `98278D827213305C7C89B6928B3448BF6444193998EAF08DABEE3AC6AB92C6DC`，与 probe_identity 相符。复用其已有展开目录比较，只改变 `Runtime/render_execute.text`，即声明的捕获钩子。
- 进程隔离：run_td_probe 启动前拒绝已有 TD 进程，并检测 127.0.0.1:5005；用隐藏进程打开 scratch 副本，保存返回 PID，finally 只停止该 PID。源工程不保存回写。本复核没有启动/停止 TD 或重跑探针。
- 12 项重开检查：现有报告全部为 true，TD build 2025.32820、22 节点、UDP loopback 5005、输入/回调/render、1280×720 输出、禁止输出节点/发送回调、节点和脚本错误、Python 权威均列入检查。审阅了生成这些检查的实现，不把报告当成本复核新启动 TD 的结果。
- 8 项链路检查：不只读取 pass 标记，还从五份状态独立重新计算，全部成立。publisher/fixture 为 LIVE；异常累计丢包 2、重复 1、乱序 1；disconnected 帧龄 2750ms；recovered 为 LIVE，三项累计统计保持 2/1/1，重连计数为 1。
- 五张新截图：逐张打开 publisher_live、fixture_good、out_of_order、disconnected、recovered，均为 1280×720 的实际 TOP 输出捕获；正文/尾行完整，无原右侧/底部裁切，SQI 条没有遮挡正文。publisher 为 dev_replay；fixture 的 actual identity 为 unavailable；异常画面有 2/1/1；断流为红徽标；恢复为绿徽标且保留统计。五张图及五份状态的哈希均与 capture_manifest 相符。捕获代码为 `output.cook(force=True)` 后 `output.save(...)`，未发现主机重绘图片代替 TD 输出的实现。
- 权限/签名：历史签收文件只绑定 `8790cd3ae4db3543c038efc21deec635605cb06f` 和 2026-09-02 傅钧烨签署。TASK、summary、当前合同均明确新候选未代签、A 主题原生 UI 未验收、真实设备/Unity 全链未完成。截图中的 LIVE/formal_stage_1 是合成消息内容，不是设备实采或研究准入证据。

## 测试与未覆盖事项

只读执行（禁用 bytecode、pytest cache 与第三方插件自动加载）：

```text
py -3.14 -B -c "import os; os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'; import pytest; raise SystemExit(pytest.main(['02-技术研发/03-TouchDesigner/t01_telemetry_panel/tests','02-技术研发/03-TouchDesigner/f04_readonly_console/tests','-q','-p','no:cacheprovider','-k','not test_host_artifacts_are_deterministic']))"
46 passed, 2 deselected in 0.08s
```

已有 `evidence/pytest.txt` 为 `48 passed in 0.11s`。另两项是 T-01/F-04 的 host 制品确定性/权限测试，会创建 tmp_path 并写 JSON，因此为遵守仅允许写本报告的限制，本复核阅读测试但没有重跑；**本复核不是独立重跑 48/48**。现有 48 项未覆盖上面的 LFS 指针对应与新增核心条目漏检，故均通过不能消除两个 P2。

未重新运行 verify.py（会写报告、host 制品及展开目录）、TD builder、repair 或 TD probe；不评审 A 主题原生控件/标签切换/多尺寸布局、真实设备、Unity 联合运行、T-02 操作通道、研究效果及真人签收。Word 和交接由主 Agent 继续完成，不作为本轮缺陷，也不将 summary 正常写入时序当作缺陷。

本复核唯一写入为本文件；未修改实现、历史制品、签署、任务状态或其他文件，未提交。

## 修复后复审（2026-09-28）

本节追加记录，不撤销或改写首轮 **2 P2 / 1 P3** 的发现与复现事实。以下结论仅针对本轮新增修复：verify.py 的两个函数及主流程接入、execution/test_verify.py 的 9 项回归、A 实施记录与 layout-review 的两处链接，以及这些变更所依赖的已有证据。

**复审结论：首轮两项 P2 和一项 P3 均关闭；额外修复的历史清理脚本链接也有效。限定复审范围内未发现新的 P0–P3 缺陷。独立实际运行 57 项通过，构成为原专项 48 项 + 验证器回归 9 项。**

### 逐项关闭与覆盖依据

| 首轮问题 / 附带修复 | 当前实现与实测 | 复审状态 |
|---|---|---|
| P2：新增核心文件漏检 | `compare_core_files` 先计算历史/当前核心集合的双向差集，再比较交集内字节；main 使用其返回的 differences 执行失败判定。直接对既有展开清单重放原 `unverified_send.text` 新增项，返回精确新增路径，不再返回空差异。 | CLOSED |
| P2：LFS 指针与物化字节未对应 | `git_artifact_policy` 解析指针字段，比较 OID 与物化 SHA-256、size 与物化长度；main 对每件制品调用该函数。原“零 OID + size 999999 + different artifact”输入现在抛出 `LFS_POINTER_IDENTITY_MISMATCH`。 | CLOSED |
| P3：A 主题构建器旧链接 | 实施记录第 8 行链接改为 Agent execution；按文档父目录解析到 `agent/tasks/T-01/execution/build_workbench_a.py`，实际文件存在。 | CLOSED |
| 附带修复：layout-review 清理脚本旧链接 | 链接解析到 `agent/tasks/T-01/archive/clean_default_demo.ps1`，实际文件存在；文案明确是历史脚本、已归档、不再执行。此项不是首轮已登记 P3 的替换或新增首轮发现。 | VERIFIED |

9 项测试均直接调用生产函数，不是复制修复逻辑或只检查通过总数。覆盖明细：

| 测试 | 展开数量 | 实际断言与原问题对应 |
|---|---:|---|
| `test_valid_git_artifact_policies[raw,text,lfs]` | 3 | 原始相同字节、Git LF/CRLF、正确 LFS OID/size 分别返回预期策略，保证负测修复没有破坏合法路径。 |
| `test_lfs_pointer_wrong_identity_rejected[oid,size]` | 2 | 一次仅改错 OID、一次仅改错 size，各自要求抛出指定错误；比首轮两字段同时错误的复现更能证明两项都参与拒绝。 |
| `test_core_comparison_covers_both_sets_and_content[added,deleted,functional,layout]` | 4 | added 使用首轮相同新增路径；deleted 检查反向缺失；functional 改变 `.n` 内 DAT 类型，要求功能差异；layout 仅改变 tile/viewport/current 选择，要求无功能差异且准确列入 layout。前三项要求恰有一项差异且没有 layout 放行，layout 正测避免把正常编辑器变化误报。 |

added 测试按首轮方式只在序列化目录清单增加条目，不写该新增文件；集合差集应在无需读取该文件时识别新增。另行使用实际历史/current 展开清单直接重放，断言返回值等于原新增路径，补充确认了测试中的数量断言确实对应原漏检对象。没有通过数量替代覆盖判断。

### 57 项实际运行

使用 Python 3.14 的 `-B`，设置 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，pytest 参数为：

```text
02-技术研发/03-TouchDesigner/t01_telemetry_panel/tests
02-技术研发/03-TouchDesigner/f04_readonly_console/tests
agent/tasks/T-01/execution/test_verify.py
-q -p no:cacheprovider
--basetemp D:\Agent\srp\.artifacts-local\task-normalization\T-01\independent-qa\recheck-d109ddd383ee42cca5c9e5276435486f

57 passed in 0.13s
```

无 deselect。原 T-01/F-04 两项 host 制品确定性/权限写盘测试本次实际运行并通过；其 tmp_path 和四项核心文件回归的临时文件均由 pytest 放在上述授权目录。运行前验证 basetemp 位于授权根内且不存在，未让 pytest 删除其他已有目录。

首次尝试因授权根尚未创建，pytest 的 basetemp 初始化出现 `FileNotFoundError`，结果为 51 passed / 6 setup errors；在授权范围补建 independent-qa 目录后重新运行，得到上述完整通过结果。此为复审命令的目录准备问题，不登记为产品缺陷。首轮只运行 46 项的历史记录仍保留，当前 57 项结果替代其未重跑两项的覆盖限制。

### 已有证据复核与边界

- 用修复后的生产函数只读复核原 23 件制品，哈希/长度与历史清单、artifact_comparison 一致：13 件 raw bytes、10 件 Git 换行规范化，**0 件实际 LFS 指针**。LFS 解析只由上述合成回归与原输入重放验证，不声称原 23 件证据触发该分支。
- 核对原/current TOE 与既有展开副本身份后，用新 `compare_core_files` 复核：49 项历史核心文件、功能差异为空、13 项仅编辑器布局变化，与首轮结果相同。
- 已有可读候选源哈希、probe 副本哈希、五张截图及五份状态的 capture_manifest 哈希均仍一致；已有报告的 12 项重开和 8 项链路检查均为 true。复审没有新启动 TD 或生成运行截图，不将其计入 57 项主机测试，也不重称为本轮 TD 实跑。
- Word 更新由主 Agent 完成，未在本次复审修改或验收 Word。正确计数为“48 原专项 + 9 验证器回归 = 57”；不扩大历史真人签收、A 主题原生 UI、真实设备/Unity 全链或研究结论的范围，首轮所列这些未覆盖事项继续开放。
- 本次持久报告只更新本文件；除此之外仅创建授权 independent-qa 测试临时目录/文件。未修改实现、其他证据、历史制品或签署，未启动 TD、联网或提交。
