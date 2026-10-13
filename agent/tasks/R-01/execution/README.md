# R-01执行入口

仓库根执行`py -3.14 agent/tasks/R-01/execution/verify.py`，或verify.ps1。使用项目既有jsonschema/pytest，不安装依赖。

validate_candidate.py从旧99_验证与清单迁入，保留候选完整性与条件匹配检查，补充实际Draft202012Validator执行。test_candidate.py覆盖合法fixture、定向负例与未列入负例的非法模式/时间/版本/字段。

verify.py记录真实退出码和Schema错误路径；与当前v1.2及F-02适用入口对应。不运行Unity、不产生问卷答案或任何真人记录。原candidate、Schema、fixture和验收原件保留共享来源，当前适用关系写入outputs。
