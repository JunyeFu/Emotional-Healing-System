"""Build the reusable Chinese task-package Word form."""
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / 'human/templates/通用中文逐包任务模板_v2.0.docx'


def table(doc, headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Table Grid'
    for cell, text in zip(t.rows[0].cells, headers):
        cell.text = text
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), 'EAF0F4')
        cell._tc.get_or_add_tcPr().append(shading)
        for run in cell.paragraphs[0].runs:
            run.bold = True
    repeat = OxmlElement('w:tblHeader')
    t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for row in rows:
        cells = t.add_row().cells
        for cell, text in zip(cells, row):
            cell.text = text
    for row in t.rows:
        no_split = OxmlElement('w:cantSplit')
        row._tr.get_or_add_trPr().append(no_split)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def heading(doc, text, prompt):
    doc.add_heading(text, level=1)
    doc.add_paragraph(prompt)


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(1.8)
    sec.left_margin = sec.right_margin = Cm(2)
    for name in ('Normal', 'Title', 'Heading 1'):
        s = doc.styles[name]
        s.font.name = 'Microsoft YaHei'
        s.font.color.rgb = RGBColor(0, 0, 0)
        s.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    normal = doc.styles['Normal']
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.12
    doc.styles['Title'].font.size = Pt(22)
    doc.styles['Heading 1'].font.size = Pt(12)
    doc.styles['Heading 1'].paragraph_format.space_before = Pt(9)
    doc.styles['Heading 1'].paragraph_format.space_after = Pt(4)
    for style in doc.styles:
        for border in list(style.element.iter(qn('w:pBdr'))):
            border.getparent().remove(border)
    footer = sec.footer.paragraphs[0]
    footer.alignment = 2
    footer.add_run('逐包任务模板 v2.0  |  ')
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    doc.core_properties.title = '通用中文逐包任务模板'
    doc.core_properties.subject = '任务领取 执行 验收 交接'
    doc.core_properties.author = ''

    doc.add_paragraph('通用中文逐包任务模板', 'Title')
    doc.add_paragraph('一包一份，结论先行。适用于科研、编程、建模、开发和投资研究；随执行增量填写，不把计划写成结果。方括号内容替换为实际信息；无关项写“不适用”，必要时增删表格行。')
    table(doc, ['任务身份', '填写内容'], [
        ('项目与任务', '[项目名称] / [编号] / 【领域】[动作与交付对象]'),
        ('版本与日期', '[文档版本] / [更新日期] / [本次审阅对象版本或提交]'),
        ('责任与领取', '[负责人] / [实施人或Agent] / [复核人] / [领取日期]'),
        ('入口与状态', '[权威任务文件可点击链接] / [注册状态] / [当前实际进展]'),
    ])
    heading(doc, '一 当前结论', '[用两句话说明本包解决什么、目前完成到哪里，以及本次需要审阅人作出的决定。]')
    doc.add_paragraph('本次请求：[仅知会 / 审阅方案 / 复核结果 / 真实责任人签收]；未关闭事项：[无，或事项与负责人]。')
    heading(doc, '二 目标与完成标准', '项目作用：[本包推动哪一项目目标]。范围：[本包承担什么，明确排除什么]。工作量：[预计人日或时间]。')
    table(doc, ['验收编号', '可检查的完成标准', '检查方式'], [
        ('AC-01', '[交付对象、预期行为或结果]', '[运行、复算、文件审阅等]'),
        ('AC-02', '[上游输入与下游接口要求]', '[消费者或交接检查]'),
    ])
    doc.add_paragraph('所需技能与资料：[必需技能、工具及实际版本、国内教学或视频链接]；接口与规范以权威原文为准。')
    heading(doc, '三 实际交付', '计划时填“拟交付”，完成后改为实物位置；链接应能打开文件或入口，不只写名称。')
    table(doc, ['交付物', '打开或运行入口', '对应验收'], [
        ('[主要交付物]', '[文件链接 / 命令 / 制品入口]', '[AC编号及当前状态]'),
    ])

    doc.add_page_break()
    heading(doc, '四 执行过程与关键决定', '输入与前置：[上游编号、实际输入位置、版本及是否就绪]。采用方案：[最终选择与一条实质理由]。')
    table(doc, ['步骤与责任人', '动作及阶段出口', '实际进展'], [
        ('1 明确输入 [人]', '[确认需求与最小可检验结果]', '[日期 / 状态 / 结果]'),
        ('2 实施 [人]', '[完成主要交付，对应AC]', '[实际变化或阻断]'),
        ('3 验证与交接 [人]', '[完成必要验证，交给消费者]', '[结果及接收情况]'),
    ])
    heading(doc, '五 验证与结果', '只记录本次实际执行的检查；未执行写明原因。测试通过、真实运行和研究结论分别表述。')
    table(doc, ['验收项', '实际验证及证据链接', '结果与可支持结论'], [
        ('[AC编号]', '[命令 / 数据 / 截图 / 日期]', '[通过、失败或未验证；结论范围]'),
        ('[AC编号]', '[重跑入口或必要来源]', '[结果、数量或测量值]'),
    ])
    doc.add_paragraph('研究、建模或投资任务按需补充：[数据与分析范围、基线比较、关键假设及结果]。不要用工程完成代替实证，也不要把回测写成未来事实。')
    heading(doc, '六 偏离与修复闭环', '按任务书、接口和项目目标检查真实偏离；没有发现时写检查范围，不列假想风险。')
    table(doc, ['问题及实际影响', '修复或裁定', '复测与责任'], [
        ('[真实问题或无]', '[修改的权威文件及内容]', '[证据 / 关闭状态 / 负责人]'),
    ])
    doc.add_paragraph('Word中的修订意见应先落实到执行文件，再更新本报告；未关闭项明确责任人与下一动作。')
    heading(doc, '七 目录与文件整理', '当前有效入口：[输入、执行、证据和交付位置]。废弃或历史材料：[保留、归档或删除的对象及理由；无则写无]。')

    doc.add_page_break()
    heading(doc, '八 上下游交接', '前向检查：下游能否直接消费本包交付。反向检查：本包是否覆盖项目目标要求，是否仍有缺口。')
    table(doc, ['关系', '交接内容与接收人', '当前条件'], [
        ('上游 [编号]', '[实际输入与权威入口]', '[就绪或缺口]'),
        ('下游 [编号]', '[交付、接口及接收人]', '[可开始或仍待何条件]'),
        ('项目总体', '[对目标、研究或产品的具体作用]', '[剩余缺口及承担任务]'),
    ])
    heading(doc, '九 审阅与责任签收', '独立Agent复核与真实责任人签收分开记录。未签收填“待签收”；不得代填姓名、日期或结论。')
    table(doc, ['审阅环节', '实际记录'], [
        ('独立复核', '[复核人或Agent / 日期 / 对象版本 / 结论 / 报告链接]'),
        ('真实责任人签收', '[姓名 / 日期 / PASS或退回 / 签收范围 / 原始记录]'),
        ('真实活动或外部条件', '[设备、现场、许可或平台回执；仅任务要求时填写]'),
    ])
    doc.add_paragraph('完成层次：[实现] / [必要验证] / [独立复核] / [责任签收] / [发布或研究准入]。逐项填写真实状态，后项不由前项自动推导。')
    heading(doc, '十 收尾与下一包', '收尾：[交付位置；任务要求时填写commit、push、PR、合并或锁定版本]。')
    doc.add_paragraph('下一包：[编号、领域与名称]；领取人：[姓名或未领取]；启动条件：[已满足或具体缺口]。下一必要动作：[一个明确动作及负责人]。')
    heading(doc, '十一 审阅来源', '任务权威：[链接]；执行与重跑入口：[链接]；本次证据：[链接]；历史签署：[链接或不适用]。来源只列支撑本包判断的材料，当前结果与历史结果分开。')
    doc.add_paragraph('使用约定：小任务保留目标、交付、验证与责任即可压缩为一页；复杂任务增加必要附件，不逐日重复叙述。同一事实只写一次，其他位置引用。')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == '__main__':
    main()
