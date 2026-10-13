# 历史记录保留与执行迁移

原第二人签署、技术验收、fixtures/golden与evidence/synthetic_stress_report.json保留原字节和当时范围。旧报告中的候选、旧目录、旧计数不覆盖为当前结果。

generate_golden_archive.py及generate_stress_report.py实际迁入execution，旧位置删除且无转发副本。新输出在evidence/runtime；归档文件按LF保留，避免Git换行转换破坏字节哈希。

共享归档、代理、重放、配置与Schema仍由技术模块维护。最终根目录迁移时统一处理，不以文件引用代替实际迁移。

模块README属于U12-06进行中输入，保留原字节；订正内容移入outputs/current-store-contract.md，根README指向当前说明。历史输入不自动刷新。
