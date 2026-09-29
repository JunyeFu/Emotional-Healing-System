# 首轮迁移失败摘要

execution/verify.py首轮专项：4 failed, 134 passed in 36.61s。此文件根据本轮实际命令返回整理，不是原始完整终端日志；handoff.txt现为修复后的138项通过输出。

- A-02 test_current_navigation：旧SAP导航目标已迁出，链接失效。
- A-05 test_candidate_signature_preserved_and_differences_recorded：将execution误作contract所在outputs目录。
- A-05 test_archived_questionnaire_and_current_navigation：同一旧SAP导航失效。
- A-04 test_sources_and_active_consumers：同一旧SAP导航失效。

已修复真实导航与A-05读取位置；未放宽测试。修复后138 passed in 33.64s，完整通过输出见handoff.txt。
