# 通用中文逐包任务模板 v5.0

当前维护入口：[LaTeX模板](通用中文逐包任务模板_v5.0.tex) · [PDF预览](通用中文逐包任务模板_v5.0.pdf)。DOCX与DOTX旧版本仅作历史参考。

1. 复制 `.tex` 到实际任务目录，按真实内容替换 `【填写】` 等占位项。
2. 启动时填写目标、责任、上游、验收与步骤；执行时回填交付和验证；收尾时填写实际签收与下游接收。删除不适用项。
3. 如需截图，取消文件末尾插图示例的注释，填写真实图片路径、图注及证明范围。文件路径使用正斜杠。
4. 使用 XeLaTeX 编译：`xelatex -interaction=nonstopmode -halt-on-error "任务副本.tex"`。链接或页码变化后再编译一次。输出为同名PDF。

模板是独立单文件，不依赖 SRP 业务数据或 Python 生成器。编译需要 fontspec、xeCJK 等标准包及黑体、微软雅黑；本机字体路径为 `C:/Windows/Fonts/`，换到其他系统时修改字体声明。标题居中加粗黑体，正文微软雅黑，PDF嵌入字体；结构为“一、二、三”及“1.1、2.1、3.1”。

当前 SRP 71包依旧先维护 `agent/tasks/<编号>/outputs/summary.json`，使用 `agent/tools/build_task_reviews.py` 生成审阅；不要在重生成前只手改生成文件。通用模板用于新任务或跨项目直接填写。统一排版实现见 `agent/tools/review_latex.py`。
