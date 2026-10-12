"""Keep F-02's approved measurement design current after baseline regeneration."""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN = 'agent/design/design-foundation-20261008/'
MARKER = '\n\n<!-- F02-MEASUREMENT-20261009 -->'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')



def render_current():
    folder = ROOT / 'agent/tasks/F-02'
    text = (folder/'TASK.md').read_text(encoding='utf-8')
    def rebase(match):
        target = match.group(1)
        if '://' in target or target.startswith('#'):
            return match.group(0)
        return '](' + Path(os.path.relpath(folder/target, folder/'outputs')).as_posix() + ')'
    return re.sub(r'\]\(([^)]+)\)', rebase, text).replace('# F-02 ', '# F-02 当前交接：', 1)


def refresh():
    folder = ROOT / 'agent/tasks/F-02'
    design = json.loads((ROOT / DESIGN / 'operational-design.json').read_text(encoding='utf-8'))
    approval = design['normalization']['design_review']
    conclusion = ('F-02原注册状态DONE及历史签收保留。2026-10-09用户批准本轮设计通过；'
                  '当前设计与材料更新已交付。中文独立复核、适用性验证和正式测量冻结仍待执行，'
                  '不以历史DONE或设计批准代替真实研究准入。')
    facts = [
        '英文PANAS-X原手册已取得（版权1994、updated 8/99，DOI 10.17077/48vt-m4t2）；PhenX180501明确允许非商业复制使用。',
        '采用一般NA10/PA10，共20题；此刻时间窗口，NA前测校正后测为主要候选，PA为次要候选。各分量1至5求和10至50，无反向，不合成20题总分；任一分量缺题则该分量缺失为项目工作规则。',
        '中文SRP-PANASX-GENERAL-ZH-DRAFT-01及指导语、锚点、计分键已交付；允许内部审阅，不是官方或已验证译本。原不自译要求已由用户授权工作初译取代。',
        '07第10、11节已提供逐题复核、独立回译输入要求、主持稿、单人记录及轮次决定表。两轮各A3/B3，累计12名不同认知学生；优先原8评审内安排2名合适语言审阅者。人选尚未落实。',
        'M01现为独立语言审阅、中文版本选定及适用性证据；M02为中文翻译/改编与公开范围核对。英文非商业复制许可不再列为待取得。20名技术前置不能独自证明新译本有效。',
    ]
    handoff = [
        'F-02负责构念与版本决定；Q-01承接语言审阅人选，Q-02承接认知访谈，U12-04核对评分及统计规格，G-05核对对应活动批准及使用范围；下一动作是落实审阅人员和中文摘录，尚不招募正式研究。',
        '原AC1至AC3保留为新范围完整验收条件，未勾选不表示设计稿未交付；真实部分须相应证据。设计通过已单独记录，不重复要求批准同一设计。',
        '07当前有效内容以.tex及编辑器预览为准；磁盘07 PDF未另行导出，不作为此次测量更新依据。F-02自己的证据PDF从本总结重新生成。',
    ]
    note = MARKER + '\n## 2026-10-09 当前测量设计与批准\n\n' + conclusion + '\n\n'
    note += '\n\n'.join(facts + handoff) + '\n\n'
    note += '[当前测量源稿](../../../design/design-foundation-20261008/07-protocol-candidate.tex)；[设计索引](../../../design/design-foundation-20261008/operational-design.json)。\n'
    for path in [folder/'TASK.md', folder/'outputs/current-measurement.md', folder/'outputs/operational-design-handoff.md']:
        text = path.read_text(encoding='utf-8').split(MARKER)[0]
        # Preserve original criteria and history, while clarifying their remaining scope.
        text = text.replace('本轮未取得唯一题本，保持未关闭。', '中文工作稿已交付，正式题本未冻结。')
        text = text.replace('不自译、不拼接、不自动换终点', '允许内部审阅初译，不冒称已验证、不拼接、不自动换终点')
        tail = note if path.parent.name == 'outputs' else note.replace('../../../design/', '../../design/')
        path.write_text(text + tail, encoding='utf-8')
    (folder/'outputs/current-measurement.md').write_text(render_current(), encoding='utf-8')
    path = folder/'outputs/summary.json'
    summary = json.loads(path.read_text(encoding='utf-8'))
    summary.update(review_date='2026-10-09', title='F-02 构念与测量设计更新审阅', conclusion=conclusion, design_review=approval)
    updates = {
        '当前结论': ['原DONE、本轮设计批准、真实验证分别记录；当前方案为固定A与受限适应B整包比较，I/G/X分离。'],
        '实际交付': facts,
        '执行过程与关键决定': ['理解题共同部分经等值核验后比较，A预设误读题与B目标/实际/不可用题分开解释。', 'I达成、G跟随、控制成本、努力及舒适独立；SCCI仅操纵检查。', '主要候选分析单位为参与者；原分配纳入目标人群，后测NA以前测和顺序校正，缺失按07候选规格处理。真实X未知不由G插补。'],
        '验证与结果': ['英文原件题项与20题工作稿NA/PA映射已有静态核对；材料和生成结果检查仅证明文档一致。', '中文回译、认知访谈、地板分布及适用性验证未执行；正式参数与N未冻结。'],
        '偏离与修复闭环': ['已删除当前生成来源中的不自译旧规则，并落实中文工作稿的真实身份。', '构念测量蓝图和候选分析规格已交付；剩余的是具体中文材料复核与实证适用性，不再把整份设计材料列为尚未交付。'],
        '上下游交接': handoff,
        '审阅与责任签收': ['用户于2026-10-09明确批准设计通过，适用于本轮设计方案和材料。历史候选审查原件及其签署边界保留，用户设计批准不冒充语言专家或真实第二人测量审阅。'],
        '收尾与下一包': ['F-02本轮文档与设计更新完成；按上述责任分工承接前置复核，取得真实证据后再冻结中文测量。业务状态保持DONE，不重新领取旧任务。'],
        '审阅来源': ['当前来源为07源稿第3、7、10、11节、operational-design.json及来源补获记录；原英文手册仅作非商业研究材料保存。'],
    }
    for section in summary['sections']:
        if section['heading'] in updates:
            section['paragraphs'] = updates[section['heading']]
    for finding in summary['findings']:
        if finding['id'] == 'F-02-DESIGN-BASELINE':
            finding.update(status='DESIGN_APPROVED_EMPIRICAL_PENDING', description=conclusion)
    sources = [DESIGN+'07-protocol-candidate.tex', DESIGN+'operational-design.json', 'agent/work/2026-10-08_科学来源补获与量表侧证.md']
    summary['source_links'] = [x for x in summary['source_links'] if x['path'] != DESIGN+'07-protocol-candidate.pdf']
    for source in sources:
        if source not in [x['path'] for x in summary['source_links']]:
            summary['source_links'].append({'path':source, 'label':'当前测量来源 '+Path(source).name})
    save(path, summary)
    for rel in ['outputs/design-revision.json', 'inputs/sources.json', 'evidence/verification.json']:
        path = folder/rel
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        value['measurement_design_update'] = {'date':'2026-10-09', 'design_review':approval['status'], 'materials':'DELIVERED', 'empirical_validation':'NOT_EXECUTED', 'formal_collection_allowed':False, 'sources':sources}
        if rel == 'inputs/sources.json':
            value['paths'] = list(dict.fromkeys(value['paths'] + sources))
            value['historical_pdf_note'] = '07磁盘PDF早于本次测量更新；当前内容读取.tex或编辑器预览。'
        save(path, value)


if __name__ == '__main__':
    refresh()
