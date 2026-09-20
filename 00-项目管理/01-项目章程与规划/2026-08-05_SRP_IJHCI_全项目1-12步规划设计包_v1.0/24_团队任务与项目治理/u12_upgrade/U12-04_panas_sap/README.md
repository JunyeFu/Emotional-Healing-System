# U12-04 PANAS 主结果 SAP 与新功效规格

任务类型：统计规格（SAP + 功效模拟规格）｜波次 W1｜4 人日｜FIXED｜process_profile=P-ANALYSIS
状态：CANDIDATE_NOT_RESEARCH_FROZEN（设计+合成证据，未做真实数据声明）

## 交付物

| 文件 | 说明 |
| --- | --- |
| `sap.md` | PANAS 主结果 SAP（12 节，对齐 protocol_authority_v1.2.json） |
| `contract.json` | 机器合同（字段级可验证） |
| `power_spec.json` | 功效模拟规格（N×效应网格，N/效应均不冻结） |
| `power_simulation.py` | 确定性 Monte Carlo 功效模拟（HC3 双侧） |
| `power_grid.json` / `power_report.md` | 功效网格与报告（运行后生成） |
| `sources.md` | 参数来源（每个参数可回溯权威输入） |
| `validate.py` | 合同一致性校验 |
| `test_contract.py` | pytest 合同测试（正反零与缺失情景） |
| `build_evidence.py` | 哈希复算与证据生成 |
| `evidence.json` | 证据清单（运行后生成） |

## 验证命令（本机无 py launcher，统一用 uv 托管 Python 3.14.7）

```powershell
$uv = "D:\Hermes\bin\uv.exe"
$dir = "D:\Agent\03-SRP\00-项目管理\01-项目章程与规划\2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0\24_团队任务与项目治理\u12_upgrade\U12-04_panas_sap"

# 1) 合同一致性校验
& $uv run --python 3.14.7 --with numpy python "$dir\validate.py"

# 2) pytest 合同测试
& $uv run --python 3.14.7 --with numpy --with pytest -m pytest -q "$dir\test_contract.py"

# 3) 功效模拟（默认 N×效应网格）
& $uv run --python 3.14.7 --with numpy --with scipy python "$dir\power_simulation.py" --output-dir $dir

# 4) 证据哈希
& $uv run --python 3.14.7 python "$dir\build_evidence.py"
```

## 验收对应

- AC1 可追溯：`sources.md` 每个参数指向 protocol_authority_v1.2.json 字段或存量惯例。
- AC2：双侧主比较（two_sided/α=0.05/HC3）；等效默认不启用；N 与界值未冻结；覆盖正反零与缺失情景（pytest + 功效双分析集）。
- AC3：`evidence.json` 与提交绑定；独立复核及真实第二人签收由任务治理流程执行。

## 未冻结项（须在真实数据可用前冻结）

minimum_important_affect_difference、missingness_and_mnar、functional_margin_justification、final_power_and_n 等 15 项（见 contract.json `required_freezes`）。本包不主张任何研究级结论。
