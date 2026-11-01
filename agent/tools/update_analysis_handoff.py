"""Bounded, repeatable migration of active analysis handoffs; preserve signed history."""
import json
from pathlib import Path
import shutil
import runpy

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = 'pre-analysis-closure-20261019'
TASKS = {
    'F-02': '核对最终NA10/PA10题键、此刻指令、前后测时点与逐题CSV；缺题只令相应分量缺失。工作译稿与正式资格分开。',
    'A-01': '消费六类输入、P-02严格封存和规范化运行/标注导出，输出只读派生的signals/events/participant_modules；I、G、X及未知分离。',
    'A-02': '按原分配构建正式参与者集；前置问卷/预试分开；四模块固定分母，传感器失效不删除有效PANAS，50次PMM及delta敏感性候选已实现。',
    'A-03': '以当前07源稿核查计分、HC3、PMM/Rubin及30/40/48/60精度情景；软件候选不能替代REAL/CAL与正式N冻结。',
    'U12-04': '当前SAP采用B-A、四天气顺序、HC3、PMM k=5/50次/20轮；旧前测代填统计器转为历史回归，不再作为活动入口。',
    'A-05': '通过唯一分析入口生成estimates/sensitivity/secondary表、六组图和中文报告；真实锁库、揭盲、正式SAP及独立复算仍待执行。',
    'U12-07': '11张表的字段规格以当前A/B整包比较更新，I达成/G跟随/未知与成本分报，真实专家重建/可选扩展保持NOT_RUN，不从合成表写发现。',
    'U12-10': '按B-A区间解释方向；跨零不是等效；情绪、执行、覆盖与成本分轴，不自动综合胜出或拆分机制因果。',
    'W-02': '消费analysis.json、结果CSV、PNG/PDF及report.md/pdf；逐项主张对应真实结果行与输入，不把SYNTHETIC样例当实证或论文成稿。',
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def preserve(path, folder):
    target = folder / path.relative_to(folder.parent.parent)
    assert target.resolve().is_relative_to(ROOT) and path.resolve().is_relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(path, target)


def refresh_a03_supplement():
    governance = ROOT / 'agent/governance/planning/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
    rendering = runpy.run_path(str(governance / '13_render_ready_task_packages.py'))
    package = governance / '当前解锁独立任务包/A-03'
    manifest_path = package / 'package_manifest.json'
    manifest = read(manifest_path)
    original_identity = (manifest['input_snapshot_id'], manifest['candidate_identity'], manifest['source_files'])
    archive = ROOT / 'agent/tasks/A-03/archive' / ARCHIVE
    for name in ('package_manifest.json', 'FILES.md', 'design_updates/12_TASK.md'):
        destination = archive / 'dispatch' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(package / name, destination)
    mapping_path = governance / '12_独立任务包文件映射_v1.0.json'
    mapping = read(mapping_path)
    update_paths = mapping['tasks']['A-03']['design_update_files']
    for source in ['agent/modules/srp_analysis/README.md', 'agent/modules/srp_analysis/statistics.py',
                   'agent/modules/srp_analysis/analysis-spec.template.json', 'agent/tasks/U12-04/outputs/sap.md']:
        if source not in update_paths:
            update_paths.append(source)
    updates = []
    for index, relative in enumerate(update_paths, 1):
        source = ROOT / relative
        destination = package / 'design_updates' / f'{index:02d}_{source.name}'
        assert source.resolve().is_relative_to(ROOT) and destination.resolve().is_relative_to(package)
        destination.write_bytes(rendering['canonical_content'](source))
        updates.append(dict(source_path=relative, package_path=destination.relative_to(package).as_posix(),
                            sha256=rendering['sha256'](source)))
    manifest['design_updates'] = updates
    manifest['analysis_software_handoff'] = {'revision': 'ANALYSIS-CLOSURE-20261019',
        'review_status': 'PENDING_NOT_HUMAN_ACCEPTANCE', 'original_input_identity_preserved': True}
    assert original_identity == (manifest['input_snapshot_id'], manifest['candidate_identity'], manifest['source_files'])
    files = (package / 'FILES.md').read_text(encoding='utf-8').split('\n## 新设计变更补充')[0].rstrip()
    files += '\n\n## 新设计变更补充（原领取输入保持）\n\n'
    files += '\n'.join(f"- [{i['source_path']}]({i['package_path']})；{i['sha256']}" for i in updates) + '\n'
    (package / 'FILES.md').write_text(files, encoding='utf-8')
    write(manifest_path, manifest)
    write(mapping_path, mapping)
    print('A-03 explicit design supplement refreshed; original input, source files and candidate unchanged.')


def main():
    for task, responsibility in TASKS.items():
        folder = ROOT / 'agent/tasks' / task
        archive = folder / 'archive' / ARCHIVE
        candidates = [folder / 'TASK.md', *(folder / 'outputs').glob('current*.md'),
                      *(folder / 'outputs').glob('current*.json'), folder / 'outputs/summary.json',
                      folder / 'inputs/sources.json']
        if task == 'U12-04':
            candidates += [folder / 'outputs/sap.md', folder / 'outputs/power_spec.json', folder / 'outputs/parameter-sources.md',
                           folder / 'execution/power_simulation.py', *list((folder / 'outputs/power').glob('*'))]
        if task == 'U12-07':
            candidates += [folder / 'outputs/table-spec.md', folder / 'outputs/reporting-rules.md']
        if task == 'U12-10':
            candidates += [folder / 'outputs/claim-rules.md']
        if task == 'A-05':
            candidates += [folder / 'outputs/analysis-report-template.json']
        for path in candidates:
            if path.is_file():
                preserve(path, archive)
        marker = '\n<!-- ANALYSIS-CLOSURE-20261019 -->'
        for path in [folder / 'TASK.md', *(folder / 'outputs').glob('current*.md')]:
            text = path.read_text(encoding='utf-8').split(marker)[0].rstrip()
            link = '../../modules/srp_analysis/README.md' if path.name == 'TASK.md' else '../../../modules/srp_analysis/README.md'
            text += (marker + '\n## 2026-10-19 数据分析软件候选交接\n\n' + responsibility + '\n\n'
                     f'[唯一入口与数据格式]({link})。活动分析采用当前07协议的固定A与原生受限适应B，不改变控制与天气。'
                     '软件实现与合成回归不继承历史验收；真实量表/设备验证、正式SAP、研究锁库和揭盲仍未关闭。'
                     '原业务状态、历史签名和领取输入快照保留。\n')
            if task == 'A-05':
                classifier = '../U12-10/outputs/current-classification.md' if path.name == 'TASK.md' else '../../U12-10/outputs/current-classification.md'
                text += f'\n结果解释消费[U12-10当前分类规则]({classifier})，不自动裁定综合胜出。\n'
            path.write_text(text, encoding='utf-8')
        summary_path = folder / 'outputs/summary.json'
        summary = read(summary_path)
        summary['analysis_software_handoff'] = {
            'revision': 'ANALYSIS-CLOSURE-20261019', 'responsibility': responsibility,
            'entrypoint': 'agent/runtime/srp-analysis.cmd', 'research_completion': 'NOT_RUN',
            'business_status_changed': False, 'claimed_input_snapshots_changed': False}
        write(summary_path, summary)
        sources_path = folder / 'inputs/sources.json'
        sources = read(sources_path)
        for name in ('README.md', 'analysis-spec.template.json', 'statistics.py', 'prepare.py'):
            ref = 'agent/modules/srp_analysis/' + name
            if ref not in sources['paths']:
                sources['paths'].append(ref)
        write(sources_path, sources)
    updates = {
        'A-01/outputs/current-rebuild.json': {'implementation': 'OFFLINE_PIPELINE_CANDIDATE_IMPLEMENTED'},
        'A-02/outputs/current-statistics.json': {'implementation': 'ANALYSIS_SET_PMM_AND_SENSITIVITY_CANDIDATE_IMPLEMENTED'},
        'A-05/outputs/current-analysis.json': {'implementation': 'ANALYSIS_REPORT_CANDIDATE_IMPLEMENTED',
                                            'result_classifier': 'B_MINUS_A_CI_CANDIDATE_IMPLEMENTED'},
        'U12-04/outputs/current-statistics.json': {'effect_scale': 'BOUNDED_NA_RAW_POINT_SHIFT',
                                                'candidate_pmm_software_delivered': True,
                                                'candidate_precision_software_delivered': True},
        'U12-07/outputs/current-writing.json': {'contrast': 'B_minus_A', 'negative_favors': 'B_native_adaptive_package',
                                               'positive_favors': 'A_fixed_open_loop_package'},
    }
    for relative, fields in updates.items():
        path = ROOT / 'agent/tasks' / relative
        value = read(path)
        value.update(fields)
        value['analysis_spec_authority'] = 'agent/tasks/U12-04/outputs/sap.md'
        value['analysis_entrypoint'] = 'agent/runtime/srp-analysis.cmd'
        value['real_data_analysis'] = 'NOT_RUN'
        value['formal_analysis_authorized'] = False
        value['historical_implementation_ref'] = f'../archive/{ARCHIVE}/outputs/{path.name}'
        if 'primary' in value:
            value['primary'].update(contrast='B_minus_A', A_code=0, B_code=1,
                                    candidate_model='NA_post ~ B + centered_NA_pre + order_2 + order_3 + order_4')
            value['primary'].pop('native_code', None)
            value['primary'].pop('abstract_code', None)
        if 'functional_guard' in value:
            value['functional_guard'].update(difference='B_minus_A', margin_candidate=None,
                                             margin_status='NOT_ENABLED_WITHOUT_FORMAL_JUSTIFICATION')
        if 'missingness' in value:
            value['missingness'].update(candidate_imputations=50, pmm_k=5, iterations=20,
                                        pooling_rules='Rubin variance with HC3 and Barnard-Rubin df',
                                        status='SAP_FREEZE_REQUIRED', model_and_mnar_grid=None)
            value['U12_04_power_missingness_implementation'] = 'PMM_CANDIDATE_NOT_FORMAL_FREEZE'
        if relative.startswith('A-02'):
            for key in ('opportunity_states', 'opportunity_completion_rate', 'pf_observable', 'pf_conservative'):
                value.pop(key, None)
            value['functional_metrics'] = {'states': ['C', 'K', 'U'], 'denominator': 'fixed_module_exposure_T',
                'lower': 'C/T', 'upper': '(C+U)/T', 'observable': 'C/(C+K)', 'unknown': 'U/T',
                'I_and_G_separate': True, 'no_legacy_noninferiority_gate': True}
        if 'not_run' in value:
            value['not_run'] = [item for item in value['not_run'] if item in
                ('real_device_decode', 'real_signal_synchronization', 'formal_data_access', 'real_data_analysis', 'human_acceptance')]
            value['not_run'] += ['real_event_validation', 'formal_parameter_freeze', 'locked_research_analysis']
        write(path, value)
    refresh_a03_supplement()
    print('Updated nine bounded task handoffs and explicit A-03 supplement; registry, signatures and claimed input identities unchanged.')


if __name__ == '__main__':
    main()
