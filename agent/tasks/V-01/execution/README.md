# V-01执行入口

仓库根执行`py -3.14 agent/tasks/V-01/execution/verify.py`或verify.ps1，使用既有pytest。

validate_historical.py只验证原签收v1.0合同与v1.1权威。validate_current.py检查当前设计候选与v1.2/U12-03关系；test_current.py用非法时序、暴露门和权限变体确认拒绝。这里不运行Unity，不修改SessionCore Schema，不签收研究时序。

outputs/current-experience.json是设计交接数据，current-experience.md解释实际使用与待接入项；evidence保留命令输出。Word从summary.json生成。
