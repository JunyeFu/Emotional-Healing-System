# SRP PDF 简报制品

本目录只保留当前固定任务概要Markdown和构建、验证入口，采用数学建模论文规范。原v1.1目标/流程简报、图及生成器已经归档，不能作为当前天气机制或研究设计。

## 制品清单

| 制品 | 源文档 | 主要用途 |
|---|---|---|
| `02_固定任务概要.pdf` | `02_固定任务概要.md` | 汇总68个固定任务、三个模板及当前状态 |

当前PDF位于[人类交付层](../../../human/deliverables/pdf/02_固定任务概要.pdf)。旧PDF见[历史简报](../../../human/deliverables/archive/README.md)，旧源文档及生成器见[Agent历史来源](../../archive/delivery/README.md)。当前任务概要不依赖旧图生成器。

## 构建与验证

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File "agent\delivery\briefs\build_briefs.ps1"
D:\MathModelingTools\envs\cumcm\python.exe "agent\delivery\briefs\verify_briefs.py"
```

构建脚本调用数学建模流水线的`build_paper.py`，以Pandoc与XeLaTeX生成统一版式。验证器检查A4、逐页文本、章节、术语及当前注册表的DONE计数和活动集合；最终仍检查实际分页和可读性。
