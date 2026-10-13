"""Apply the reviewed fixed-vs-adaptive design to existing task packages."""
from pathlib import Path
import csv
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / 'agent/governance/planning/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
BASELINE = ROOT / 'agent/design/design-foundation-20261008/task-baseline.json'


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def archive(path, folder):
    if path.is_file():
        target = folder / path.name
        if not target.exists():
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def apply():
    data = json.loads(BASELINE.read_text(encoding='utf-8'))
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames)
        rows = list(reader)
    added = ['design_baseline_id', 'design_revision_state', 'current_deliverables', 'current_acceptance_criteria', 'current_evidence_required', 'current_completion_condition']
    for field in added:
        if field not in fields:
            fields.append(field)
    for row in rows:
        task = row['task_id']
        item = data['tasks'][task]
        row.update(design_baseline_id=data['baseline_id'], design_revision_state=item['revision_state'],
                   current_deliverables=';'.join(item['deliverables']),
                   current_acceptance_criteria='；'.join(item['acceptance_criteria']),
                   current_evidence_required=';'.join(item['evidence_required']),
                   current_completion_condition=item['completion_condition'])
        folder = ROOT / 'agent/tasks' / task
        old = folder / 'archive/pre-design-baseline-20261008'
        archive(folder / 'TASK.md', old)
        archive(folder / 'outputs/summary.json', old)
        source = json.loads((folder / 'inputs/sources.json').read_text(encoding='utf-8-sig'))
        for path in [BASELINE.relative_to(ROOT).as_posix(), *data['design_sources']]:
            if path not in source['paths']:
                source['paths'].append(path)
        source['design_baseline_id'] = data['baseline_id']
        save_json(folder / 'inputs/sources.json', source)
        revision = {'task_id':task, 'baseline_id':data['baseline_id'], **item,
                    'formal_collection_allowed':False,
                    'historical_status_is_new_scope_completion':False,
                    'design_source':BASELINE.relative_to(ROOT).as_posix()}
        save_json(folder / 'outputs/design-revision.json', revision)
        common = '\n'.join('- ' + text for text in data['shared_rules'])
        deps = '、'.join(item['depends_on_original']) or '无'
        body = f"""# {task} {item['scope']}

基线 `{data['baseline_id']}`。注册状态 `{row['status']}` 保留原范围；新修订需求 `{item['revision_state']}`。本包当前设计要求优先于下方链接的旧材料，不把历史DONE转移为新适应方案验收。

## 当前任务范围

{common}

本包处理：{item['scope']}。类型：{item['disposition']}。既有依赖：{deps}；依赖的历史DONE不能证明新范围已交接。领取人 `{row['claimant'] or '未领取'}`，复核人 `{row['reviewer'] or '未指定'}`，原预计{row['effort_person_days']}人日仅历史估算，新范围成本待承接者评估。

## 交付与验收

"""
        body += '\n'.join('- ' + text for text in item['deliverables']) + '\n\n'
        body += '\n'.join('- [ ] ' + text for text in item['acceptance_criteria']) + '\n\n'
        body += '必需证据：' + '；'.join(item['evidence_required']) + '。\n\n' + item['completion_condition'] + '\n\n'
        body += """## 执行顺序与当前验证边界

1. 核对[设计修订记录](outputs/design-revision.json)、[基石主稿](../../design/design-foundation-20261008/01-design.pdf)及上游新范围；明确待冻结项。
2. 完成本包专项设计/候选修订，在原权威路径工作；需修改接口或正式协议时先由对应合同与冻结任务承接，不以文档刷新替代批准。
3. 执行与新范围对应的真实验证，保留未通过项。原execution/verify.ps1仍只核查旧实现范围，其通过不证明新控制、测量或研究完成。任务体系内容检查使用agent/tools/verify_task_design_baseline.py。
4. 同步当前输出和证据，再生成human/tasks/{task}/summary.tex及PDF；取得真实复核后才按治理流程改变业务状态。

## 输入、历史与交接

inputs/sources.json列出当前设计来源；领取中原input_snapshot_id及候选身份保留，新增要求通过分发补充和影响记录交接，不静默替换领取输入。旧TASK与总结见archive/pre-design-baseline-20261008，原审核信息和实际代码证据保留原时间/范围。大型工程以项目工作目录引用，不复制缓存。
""".replace('{task}', task)
        (folder / 'TASK.md').write_text(body, encoding='utf-8')
        current_files = [p for p in (folder/'outputs').glob('current*.md') if 'implementation-evidence' not in p.name]
        for current in current_files:
            archive(current, old)
            text = f'# {task} 当前交接：{item["scope"]}\n\n' + body.split('## 当前任务范围',1)[1]
            text += f'\n本文件历史正文：[原范围记录](../archive/pre-design-baseline-20261008/{current.name})。历史运行与候选事实仍可查，但不得以旧同反馈要求驱动新设计。\n'
            current.write_text(text, encoding='utf-8')
            for wrong, right in [('](outputs/design-revision.json)', '](design-revision.json)'),('](../../design/', '](../../../design/')]:
                text = text.replace(wrong, right)
            current.write_text(text, encoding='utf-8')
        summary_path = folder/'outputs/summary.json'
        summary = json.loads((old/'summary.json').read_text(encoding='utf-8-sig'))
        summary['design_baseline_id'] = data['baseline_id']
        summary['review_date'] = data['updated']
        summary['title'] = task + ' ' + item['scope'] + ('' if task in {'P-02','X-03','U12-01','U12-06'} else ' · 新基线审阅')
        summary['conclusion'] = f"{task}注册状态{row['status']}仅保留原范围。当前任务更新为{item['scope']}；处理类型{item['disposition']}。任务正文、设计输入、验收与人类PDF按新基线同步；新的业务证据及真实签收尚未由本次文档更新取得。"
        paras = [
            ['本包采用固定A与受限适应B整包基线；共享I、独立G/X及同预算。新设计、真实运行与正式许可分别成立。'],
            item['acceptance_criteria'],
            ['本轮交付当前TASK、专项交接、design-revision.json及来源更新；不声称运行或研究已完成。', *item['deliverables']],
            [*data['shared_rules'][:5], '本包专项：' + item['scope']],
            ['任务包/PDF/来源一致性由verify_task_design_baseline.py和build_task_reviews.py --check核查；这些静态结果仅证明当前文档一致。', '原软件测试与签收见archive/pre-design-baseline-20261008/summary.json，保持原范围，不能支持本包新增要求。'],
            ['旧同反馈与固定Target口径已从当前任务范围撤回；旧PF界、原功效或同Actual题不能自动复用。', '真实缺口：' + '；'.join(item['evidence_required'])],
            ['旧任务、总结及被替代交接保存在archive/pre-design-baseline-20261008；当前设计用LaTeX/PDF维护，不新增DOCX。'],
            ['原依赖：' + deps + '；必须核对新范围交接，原DONE不自动证明修订完成。', '消费design-foundation-20261008主稿、科学附录、决策影响和14项审稿攻击；本包真实证据：' + '；'.join(item['evidence_required'])],
            ['原签收保持下列历史信息；本轮无新增业务签收。', item['completion_condition']],
            ['新修订状态：' + item['revision_state'], '先完成本包当前验收，再按实际依赖交接；可选策略扩展不成为首版核心研究依赖。'],
            ['当前来源：task-baseline.json与基石四份LaTeX/PDF；历史来源见归档总结。']]
        for section, paragraphs in zip(summary['sections'], paras):
            section['paragraphs'] = paragraphs
        for figure in summary.get('figures', []):
            figure['caption'] = '历史资产参考，非新双条件或受限适应运行证据。' + figure['caption']
        summary['findings'].append({'id':task+'-DESIGN-BASELINE','status':'PLAN_UPDATED_EVIDENCE_PENDING','description':item['scope']+'；新业务证据未由文档刷新取得。'})
        links = {item['path'] for item in summary.get('source_links', [])}
        for name in ['task-baseline.json','01-design.pdf','02-science.pdf','03-decisions.pdf','04-review-audit.pdf']:
            path = 'agent/design/design-foundation-20261008/' + name
            if path not in links:
                summary.setdefault('source_links',[]).append({'path':path,'label':'当前设计基线 '+name})
        save_json(summary_path, summary)
        for current in (folder / 'outputs').glob('current*.json'):
            value = json.loads(current.read_text(encoding='utf-8-sig'))
            value['design_baseline_id'] = data['baseline_id']
            value['current_design_revision'] = f'agent/tasks/{task}/outputs/design-revision.json'
            value['existing_runtime_fields_scope'] = 'ORIGINAL_IMPLEMENTATION_FACTS_NOT_NEW_DESIGN_ACCEPTANCE'
            save_json(current, value)
        evidence_path = folder/'evidence/verification.json'
        evidence = json.loads(evidence_path.read_text(encoding='utf-8-sig'))
        evidence['design_baseline_id'] = data['baseline_id']
        evidence['new_scope_verification'] = 'DOCUMENT_CONSISTENCY_ONLY_BUSINESS_EVIDENCE_PENDING'
        evidence['historical_checks_scope'] = 'ORIGINAL_IMPLEMENTATION_NOT_NEW_ADAPTIVE_DESIGN'
        save_json(evidence_path, evidence)
    with (GOV/'05_可领取任务包.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    if (BASELINE.parent / 'operational-design.json').exists():
        from sync_operational_design import sync
        sync()
    print('Updated task plans, sources, summaries and registry: '+str(len(rows)))

if __name__ == '__main__':
    apply()
