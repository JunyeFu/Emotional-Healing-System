# T-01【TouchDesigner】只读遥测面板规范化

原任务状态DONE、约3人日、实施人为Codex Agent（T-01独立工作树）；真实第二人傅钧烨于2026-09-02签收候选8790cd3ae4db3543c038efc21deec635605cb06f。本轮执行人Codex，整理状态单独记录，不代填新候选真人签署。

## 目标与验收

- AC1：F-05合法遥测能正确显示设备、SQI、显式步骤与时钟字段。
- AC2：丢包、重复、乱序、2秒断流与恢复正确，接收纪元变化保留累计统计。
- AC3：只监听127.0.0.1:5005，不写回Python流程，不新增T-02请求权限。
- 本轮：执行入口实际迁入execution；历史来源与新候选隔离；当前代码专项测试、制品身份及实际TD探针验证；Word与Agent结果一致。

## 过程

1. 读取注册表、原签署、模块与A主题设计，区分历史基线和未签收候选。
2. 迁移五个Python脚本，过期清理脚本移入archive，修复真实路径及候选输出。
3. 执行verify.py；隔离副本中运行TD重开和五阶段UDP探针，逐张检查截图。
4. 发现旧Text TOP裁切时，生成独立可读候选并复测，不覆盖原TOE/TOX。
5. 从outputs/summary.json生成本包及串联Word，逐页审阅后明确路径提交推送。

## 文件与接口

inputs保存来源引用；execution为单一当前执行入口；evidence保存本轮结果；outputs保存当前使用合同与结构化总结；archive保存有明确理由的旧工具。共享运行模块、历史制品和设计原件仍留原模块，待最终整体迁移。

Python SessionCore为流程和时钟权威，T-01只读消费UDP。v2.2使用显式cycle/step，正式v2.1拒绝，dev_replay兼容但不猜步骤。TD本地帧龄和链路统计不等于设备到屏幕延迟。参与者Unity体验不依赖TD。

## 技能与资料

Python、UDP、TouchDesigner DAT/TOP与参数布局。国内教学资料消费[技能资料表的L-TD](../../../00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/08_任务技能与国内学习资料_v1.0.md)；接口查阅[Execute DAT](https://derivative.ca/UserGuide/Execute_DAT)、[Text TOP](https://derivative.ca/UserGuide/Text_TOP)及[官方中文Python socket](https://docs.python.org/zh-cn/3/library/socket.html)。版本采用项目实际基线2025.32820，不在工具缺失时自行升级。

## 交接

上游F-01/F-04/F-05提供合同、静态壳与显式步骤；P-01发布，P-02存储。T-02实现独立请求/回执/审计通道与工作台功能，不能从本包只读权限推导操作权限。A主题尚待TD内构建、导航与尺寸验收；真实设备和全链由D/S/I任务完成。下一规范化包R-01。
