# B-03合成fixture复测

初次专项143通过、1失败：测试finish传入连字符原因码SYNTHETIC-B03-NOT-EXPERIENCE，不符合既有P-01原因码合同，返回INVALID_REASON_CODE。初次输出保留initial-handoff.txt及initial-checks.json。

只把合成fixture改为已支持SYNTHETIC_TEST，不放宽运行合同。该场仅开发prepare后finish并封存，未实际启动体验；固定重放通过也不能证明动态策略运行或800秒真实全链。复测实际结果见handoff.txt和verification.json。
