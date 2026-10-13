# 历史保留及旧入口整理

位置更新 2026-09-29：下文保留逐包整理时的归档决定与当时进度，旧路径和“待迁移”表述仅解释历史。19项根目录迁移现已落实；当前物理归属见[根目录归属表](../../../root-layout.json)，实际入口以本包TASK及outputs/current文档为准。

旧validate_v01_experience_contract.py已实际迁到execution/validate_historical.py并删除原入口。明确验证签署时的v1.1权威，不再称“live authority”。原候选JSON、五份设计稿、README、独立复核和签署仍保留原目录，V-02等原始消费不改。

当前旅程在outputs单独版本化。不能回改原12节点合同来让旧校验器通过新时序，也不能把原签名转到当前14节点候选。未复制原设计稿为多份新权威。
