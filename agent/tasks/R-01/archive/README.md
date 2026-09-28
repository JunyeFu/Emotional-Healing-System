# 历史与移除说明

2026-08-06候选设计、Schema、fixture和验收原件保留原设计目录。它们是共享来源及已领取任务冻结输入，不移走、不重签，也不把旧研究门改写成新口径。

旧99_验证与清单/validate_r01_package.py实际迁入execution/validate_candidate.py；原入口删除，没有兼容转发。旧实现只检查JSON标记与负例形状，未调用Schema验证器，本轮补足真实Schema验证。

候选正文的重复内嵌Schema/fixture仅属于历史文档，不再复制为新的执行输入。当前执行只读取独立JSON原件。没有证据支持删除原研究材料，故不按文件年代清除。
