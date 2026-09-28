# 开发样片首跑阻断

首跑BuildPlayer返回1，日志为UNCONTROLLED_DEVELOPMENT_BUILD。独立Agent Raman确认P2：开发构建未通过F-03作用域授权入口。未绕过正式门；修复为复用F03BuildAuthorization.Begin并在离开作用域时恢复环境。

旧日志保留此处。新的evidence/runtime/demo记录修复后真实构建及捕获；原签收视频仍保留archive/evidence-v1，不替换历史签收。
