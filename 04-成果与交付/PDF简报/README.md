# SRP PDF 简报制品

本目录保存三份v1.1简报的Markdown源文档、项目自有插图和可复现构建脚本。内容已同步IJHCI独立审稿裁定、联合Gate 2、机会分母PF、参与者分组策略审计和产能门；版式统一采用数学建模论文规范。

## 制品清单

| 制品 | 源文档 | 主要用途 |
|---|---|---|
| `01_项目目标介绍与可行性论证.pdf` | `01_项目目标介绍与可行性论证.md` | 说明项目目标、边界、可行性与风险门禁 |
| `02_固定任务概要.pdf` | `02_固定任务概要.md` | 汇总48个固定任务、三类模板及统一验收规则 |
| `03_项目设计简述与实验流程.pdf` | `03_项目设计简述与实验流程.md` | 说明四个复合模块、系统边界、单次体验和三阶段流程 |

最终 PDF 位于项目根目录 `output/pdf/`。插图由 `generate_brief_figures.py` 生成，避免依赖外部图像资源。

## 构建与验证

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File "04-成果与交付\PDF简报\build_briefs.ps1"
D:\MathModelingTools\envs\cumcm\python.exe "04-成果与交付\PDF简报\verify_briefs.py"
```

构建脚本调用数学建模流水线的 `build_paper.py`，以 Pandoc 与 XeLaTeX 生成统一版式。验证器检查文件存在性、A4 尺寸、逐页文本、关键章节、未解析标记和术语边界；最终仍需配合逐页渲染检查图表、分页和可读性。
