# SRP × IJHCI 第四步执行包 v1.0

本目录把科研立项第一至第三步转化为预试实现所需的架构、Schema、配置和工具。

## 内容

- `2026-08-05_IJHCI科研立项第四步_研究实施架构数据契约与可复现执行包冻结_v1.0.md`
- `TASK_TREE.md`
- `contracts/event-envelope.schema.json`
- `contracts/experiment-manifest.schema.json`
- `config/protocols.v1.yaml`
- `config/experiment_manifest.example.yaml`
- `tools/generate_randomization.py`
- `tools/validate_session.py`
- `tools/verify_package.py`
- `examples/session_P0001_S1/`

## 快速验证

```bash
python tools/verify_package.py
python tools/generate_randomization.py --n 104 --seed 20260805 --output-dir allocation_example
python tools/validate_session.py examples/session_P0001_S1
```

## 研究边界

- 本包可用于 Level B/C 预试实现。
- 不表示伦理已经批准。
- 不得用示例会话替代真实实验。
- `fade` 循环叹息精确时间包络仍是正式阻断项。
