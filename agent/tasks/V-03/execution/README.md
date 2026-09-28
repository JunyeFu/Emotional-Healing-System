# 执行入口

运行 `powershell -File agent/tasks/V-03/execution/verify.ps1`。历史准备和历史交付校验分开，后者从签收候选Git读取当时manifest/许可台账，并按已观测CRLF证据还原验证，不拿当前文件去否定历史签收。

generate_historical.py保留原设计生成函数。直接运行只写outputs/historical-rebuild，不再覆盖已签署原件；其资产函数默认使用当前manifest，历史复算显式传入历史字节。历史语义不是当前运行配置。

build_current.py从原40行及当前V-02裁定生成当前使用映射与依赖差异；它不是F-05网络消息或Unity参数冻结。validate_current.py检查40行、v2.2字段存在性及当前包登记，专项测试不表示许可放行。测试缓存不纳入交付。
