# X-01迁移与消费者影响

## 实际迁移

- `agent/modules/08-随机化/verify_x01.py`移到`agent/tasks/X-01/execution/verify_x01.py`。
- 同模块`generate_evidence.py`移到同一execution目录；必须显式传入不存在的`--output-root`，不覆盖原证据。
- 原README原文移到archive，原位置改导航；原字节指纹见archive/README.md。
- `agent/modules/tests/randomization/test_verifier.py`实际导入新路径，无旧工具转发或双份执行权威。

## 消费边界

验证器可检查新目录，但Schema始终读取唯一业务模块。六份原合成材料语义重建相同；正式清单使用业务write_plan排他创建，合成工具不提供正式运行证据。历史工具命令作为原记录保留，当前命令以TASK及模块导航为准。

P-01仍拥有编排、时钟和暴露；G-02供预约，G-05落实实际岗位、存储与资格。Level C和X-03适配未交付，不放宽清单阶段检查；核心论文不要求可选阶段三已运行。

业务、Schema、配置、六份原证据、历史独立复核与签署相对43d1a4b无修改，专项直接检查。注册表、进行中输入及历史签署不因工具整理变更。共享模块迁入agent最终目录时仍须修复这些实际消费者。
