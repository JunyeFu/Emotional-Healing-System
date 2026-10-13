# Z-01 偏离与复测

首次实际环境权威检查有三项错误：旧绝对目录、直接依赖漏两项、校验器要求MCP浮动分支。现按既有工程订正，保留旧机器清单/说明逐字节原件；初始输出转录标明非原日志。没有更改软件、Unity包锁或下游正式准入。

首次专项21项通过1项失败，新测试误读CSV的`dependencies`字段；真实字段是`depends_on`。修复测试，不修改任务依赖，原pytest输出保存`initial-test-field-failure.txt`。同时对子进程开启UTF-8以正确呈现中文路径。复测结果见check-1.txt及verification.json。
