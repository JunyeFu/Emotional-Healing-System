# T-01 A主题可读性候选

保留浅色主题、只读职责、127.0.0.1:5005与20 Hz显示上限。此次只调整原生TD呈现，不修改通信合同，也不启用工具栏命令。

## 布局

1280×720为最小设计尺寸。外边距16、分区间距8、文字左右内边距12；字体为微软雅黑，正文16、关键值及分区标题18、项目标题24。较大窗口增加列宽，字号不变。

顶栏和三页导航之下依次为会话信息、设备与跟随对照、交互反馈与降级、接收统计、固定底栏。设备区40%，跟随区60%。标签左对齐，数值右对齐，状态及统计居中。总览只缩略过长会话ID；链路页保留完整字段，支持选择复制、换行和独立滚动。审计页显示真实的未接入空状态。

背景为#F2F5F8，正文白色。设备标题带#E4F1EF、对照标题带#E8EFF8、其余标题带#E9EDF2。边界和细行线取代大块空白；不采用阴影或嵌套卡片。接收蓝色、正常绿色、降级琥珀色、不可用及断流红色、等待及未知灰色，均配文字。SQI条只显示已有数值，不设置新阈值。

工具栏使用40×40禁用按钮、离线Lucide图标及原生悬浮名称。导出、截图、人工标记、中止请求仍由T-02接入。

## 依据

- [Dashboard Design Patterns](https://arxiv.org/html/2205.00757v2)：功能分组、上下分层、比较表格和总览/明细分离是本项目选择，不代表已经证实阅读效率提升。
- [Carbon表格规格](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/specifications)：参考统一间距、表头、行分隔及列对齐。
- [Grafana监控设计](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/)：参考信息层级与一致颜色语义。
- [TD布局](https://derivative.ca/UserGuide/COMP_Children_Page)、[Text COMP](https://derivative.ca/UserGuide/Text_COMP)、[PanelCOMP交互](https://derivative.ca/UserGuide/PanelCOMP_Class)：实现为Container/Text COMP和原生Panel Execute回调，不是网页或效果图。
- [WCAG文字对比](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)、[非文字对比](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)、[颜色使用](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)：借用普通文字4.5:1、必要状态标识3:1和非仅颜色提示的设计指标，不宣称整个TD程序符合WCAG。

## 实现与验证入口

`execution/build_workbench_a.py`构建新候选；`execution/capture_workbench.py`在源工程的隔离副本中实跑SDK点击、滚动与截图。输入为开发fixture。截图报告分别记录布局尺寸和实际TOP导出尺寸，不放大图像充当高分辨率证据。历史制品、签署和任务状态不改写。

当前完成的检查与候选见[2026-10-08原生证据](../evidence/readable-v2-20261008-110024/README.md)。
