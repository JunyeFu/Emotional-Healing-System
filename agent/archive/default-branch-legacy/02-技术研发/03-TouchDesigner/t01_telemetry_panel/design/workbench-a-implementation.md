# A主题原生面板实施候选

2026-09-08。状态：`HOST_TESTED_AWAITING_TD_EXECUTION`。

## 本轮代码

- [workbench_view.py](../workbench_view.py)：纯只读显示映射；保留周期和步骤身份，缺值不补零，开发回放与断流历史值明确标识。
- [build_workbench_a.py](../build_workbench_a.py)：在现有T-01内新增WorkbenchA原生候选，复用原UDP适配器，不创建网络输出。三页分别为总览、链路与时钟、事件与审计。
- 使用Container/Text/Button COMP与Panel Execute DAT；运行逻辑放Base COMP。总览短文本按可用区域收束，完整字段在详情逐行显示并支持滚动。业务字段不可编辑。
- 显示回调最高20Hz，文字只在变化时写入；SQI未知为空。导出、截图、人工标记和中止按钮禁用。
- 成功构建后禁用旧文本刷新，将Output与Perform入口指向候选原生面板；另存`T01_Workbench_A.candidate.toe`。源TOE和TOX不覆盖。失败时恢复旧显示绑定并清除本次新增节点。
- 旧ConsoleShell与后台容器暂保留在候选中，待原生运行检查通过再移除旧显示和完成Base组织迁移，不提前破坏原运行基线。

## 在当前TD中执行

打开主工程，在Python Textport执行：

```python
from pathlib import Path; p = Path(project.folder) / 'build_workbench_a.py'; exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'), dict(globals(), __file__=str(p), __name__='__main__'))
```

成功应输出`WORKBENCH_A_CANDIDATE_SAVED`及候选路径。打开`/project1/T01_TelemetryPanel/WorkbenchA`的独立面板查看或使用Perform窗口。如果出现异常，不保存覆盖主工程，保留完整Textport错误用于修正。

## 验证状态

- 主机专项测试：27 passed，包括既有17项和新增10个测试实例。覆盖缺值/零值、真实合同fixture字段、快照不变、断流历史标识、非法包、长ID完整保留、百分比和回调语法。
- 数据为合同fixture，不是真实采集证据。尚无新TOE/TOX、截图、点击或TD错误检查结果；自动化接口仍为`ECONNREFUSED 127.0.0.1:9981`。
- 待TD内确认字体和参数兼容、三个Tab、禁用按钮、双尺寸和DPI、长字段、等待/接收/断流/恢复，以及唯一UDP输入。机器生成的新节点与权限清单需在运行检查后纳入候选证据。
- 不修改注册表、独立包快照或原签收；不声称UI01-UI20全部完成，T-02与导出仍未实现。

## 官方依据

- [Text COMP](https://derivative.ca/UserGuide/Text_COMP)：原生文字、只读选择、多行与换行；格式代码关闭，避免输入内容改变显示样式。
- [COMP Layout](https://derivative.ca/UserGuide/COMP_Layout_Page)：Fill、权重、Panel Units、Align Order。
- [Panel Execute](https://derivative.ca/UserGuide/Panel_Execute_DAT)：点击值变化驱动本地Tab切换。
- [OP Viewer TOP](https://derivative.ca/UserGuide/OP_Viewer_TOP)：面板输出为TOP；实际点击入口直接使用Perform绑定的原生Panel，不依赖弃用的TOP交互参数。
