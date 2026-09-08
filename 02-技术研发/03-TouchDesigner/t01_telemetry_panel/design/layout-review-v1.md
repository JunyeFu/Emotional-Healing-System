# T-01 默认演示清理与布局复核

日期：2026-09-08。结论：保留A主题与v3信息架构，局部重建显示层，规范化非显示组件，不重写遥测适配器。

## 已完成的清理

- 使用安装版本自带 toeexpand / toecollapse，先在仓库 tmp 中处理副本，再回读验证后替换磁盘 T01_TelemetryPanel.toe。
- 删除 `/project1/geo1`（含内部节点）、`noise1`、`chopto1`、`displace1`、`moviefilein1`、默认 `out1`，共21个序列化条目。保留系统 `/local`、`/perform` 与全部 T-01 内容。
- 原工程 `project1.parm` 的 `top 0 ./out1` 仍指向演示输出，现改为 `./T01_TelemetryPanel/Output/display_out`。构建脚本同步设置该入口，不再遗漏。
- 清理前后T-01组件内49个展开文件SHA-256逐项相同。`.tox`无需修改，因为删除对象位于它的导出根之外。
- [清理报告](default-demo-cleanup-report.json)记录精确前后哈希；[清理脚本](../clean_default_demo.ps1)只生成候选，不自行替换源工程。
- 自动化接口 `127.0.0.1:9981` 返回 ECONNREFUSED，未关闭当前TD进程、未声称当前窗口已刷新或新工程运行验收通过。当前窗口可能仍持有旧工程；重新加载磁盘工程前应处理窗口内未保存改动，不能把旧窗口再次保存覆盖本次清理。
- 旧工程可从本次提交的父版本恢复；旧运行截图和签收报告保留历史身份，不把新TOE哈希代填到旧运行证据。

官方支持 `.toe` 展开为文本、修改后重新打包：[工程文件说明](https://derivative.ca/UserGuide/.toe)、[toecollapse](https://docs.derivative.ca/Toecollapse)。本轮完成离线结构验证，重开验证仍待TD自动化恢复。

## 排布裁定

| 层次 | 现状 | 裁定与最小改动 |
|---|---|---|
| 信息分区 | v3按会话、设备、跟随、反馈、降级组织，详细时钟独立分页 | 保留，不重新生图或重做产品设计 |
| 实际显示 | 单一Text TOP拼整页文本、Rectangle TOP叠加；旧1280x720截图已有裁切 | 局部重建ConsoleShell，独立文字和表格区域，不继续压缩整页文字 |
| 后端组织 | Sources、Runtime、Output全部使用Container COMP | 下次显示层重建时改为Base COMP，保留绝对路径与职责；避免非显示容器参与面板子项布局。这是本项目选择，不是官方禁止Container |
| 面板布局 | 构建脚本未设置明确的Children对齐与分页层级 | 使用纵向行、横向列、Fill权重、Align Order和间距；不要靠网络编辑器节点坐标决定用户界面 |
| 网络编辑器 | 构建脚本只给根节点设置位置，子节点缺少系统排布 | Sources -> Runtime -> ConsoleShell -> Output按左到右，回调和证据表分行；编辑器排布与Panel布局分别设置 |
| 文字与单位 | 预览画布像素被直接当布局尺寸 | TD用Panel Units；固定正文层级，确认Window COMP DPI策略，再测1280x720、1600x900和Windows缩放 |
| 执行刷新 | read_snapshot有20Hz节流，但onFrameStart每帧仍写DAT和Text TOP | 在原生显示重建中仅在快照变化时写UI，保留断流状态更新时间；不能声称当前全部渲染写操作已限20Hz |
| 按钮 | 当前TOP输出只是画面，没有T-02操作回调 | 用原生Button COMP和显式禁用状态；不在背景图上放隐形点击热区 |

依据官方说明，Panel组件用于交互二维界面；Base没有Panel参数，适合非显示网络封装。[Panel Component](https://derivative.ca/UserGuide/Panel_Component)、[Base COMP](https://docs.derivative.ca/Base_COMP)。

Children页提供对齐、间距、Align Order、Fit、裁剪和滚动；Layout页定义尺寸、Fill和层叠顺序。[Children页](https://derivative.ca/UserGuide/COMP_Children_Page)、[Layout页](https://derivative.ca/UserGuide/COMP_Layout_Page)。优先正确分配空间，不能用裁剪掩盖关键字段溢出。父容器填充与子项权重可按[官方布局课程](https://learn.derivative.ca/courses/100-fundamentals/lessons/105-comps-interfaces-organization-outputs/topic/panel-layout-and-organization/)实现。

## 下一次实施顺序

1. 恢复TD自动化连接，重开清理后的TOE，确认默认节点消失、显示绑定正确且无新节点错误。
2. 保留T01TelemetryAdapter及协议校验；仅重建ConsoleShell原生布局，非显示组织同步改为Base并更新节点权限计划。
3. 以v3二十项清单分开验证已有输入和待实现入口；新增请求及导出不混入T-01只读签收。
4. 完成等待、长文本、断流、恢复、降级和双尺寸/DPI截图，再生成新TOE/TOX及对应证据。

## 本轮验证

- 工程回读：演示条目0，T-01文件49/49字节一致，显示绑定正确。
- 首轮副本打包暴露TOC换行要求：CRLF使toecollapse把CR当文件名字符；脚本固定LF后通过完整回读。失败副本未覆盖源工程。
- 本轮未进行原生显示层重建或新运行验收；验证边界见清理报告。
