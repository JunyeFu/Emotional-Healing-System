# 执行入口

在仓库根运行 `powershell -File agent/tasks/V-02/execution/verify.ps1`。

`validate_historical.py`检查原签收v1.0及当时权威；不是当前视觉验证。`validate_current.py`检查当前交接约束及原V-04来源；`test_current.py`复现本轮发现的旧规则误用。`verify.py`执行命令并记录结果。没有Unity渲染或真实参与者测试。
