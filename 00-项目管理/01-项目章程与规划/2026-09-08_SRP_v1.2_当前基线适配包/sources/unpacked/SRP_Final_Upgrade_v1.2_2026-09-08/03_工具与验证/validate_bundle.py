"""Validate this delivery, not the original source repository or human approvals.

Default prints JSON and does not change packaged reports. --output can write a
new report; prefer a path outside a sealed/checksummed package.
"""
from __future__ import annotations
import argparse
import io
import json
import sys
import unittest
from pathlib import Path
from apply_upgrade import PACKAGE,NEW_PREFIX,validate_graph,verify_integrity,MigrationError

sys.dont_write_bytecode=True

def run_validation() -> dict:
    structural=[]
    def check(name,condition):
        structural.append({'name':name,'passed':bool(condition)})
    cfg=PACKAGE/'02_仓库升级';ov=cfg/'overlay'/NEW_PREFIX
    p=json.loads((ov/'protocol_authority_v1.2.json').read_text())
    route=json.loads((ov/'route_contract_v1.2.json').read_text())
    template=json.loads((ov/'study_manifest_v1.2.template.json').read_text())
    json_paths=list(PACKAGE.rglob('*.json'))
    for path in json_paths:
        # Generated validation report is data, not a current model input.
        json.loads(path.read_text(encoding='utf-8-sig'))
    check('all_json_parse',True)
    validate_graph(route['tasks'],route);check('reviewed_graph_acyclic_core_independent',True)
    check('70_nodes',len(route['tasks'])==70)
    check('800_second_timeline',p['core_experience']['recommended_total_seconds']==4*sum(p['core_experience']['segments_seconds'].values())==800)
    check('main_stage1_affect_two_sided',p['primary']['stage']=='stage_1' and p['primary']['test']=='two_sided' and p['primary']['alpha']==.05)
    check('no_significance_conditioned_reporting',p['primary']['report_even_if_functional_guard_fails'] and not p['functional_guard']['blocks_affect_reporting'])
    check('equivalence_not_enabled',not p['equivalence']['confirmatory_enabled'] and p['equivalence']['margin'] is None)
    check('formal_collect_stays_blocked',not p['formal_participant_collection_allowed'] and not template['formal_collection_allowed'])
    check('final_N_not_fabricated',p['sample_planning']['formal_randomized_n'] is None and template['final_randomized_n'] is None)
    check('runtime_integration_not_claimed',p['runtime_integration_status']=='NOT_IMPLEMENTED_BY_THIS_PACKAGE')
    check('template_not_an_approval',template['document_type']=='UNFILLED_TEMPLATE_NOT_APPROVAL' and template['preregistration_receipt'] is None)
    check('native_not_hidden',p['conditions']['native_is_not_hidden'] and not p['conditions']['explicitness_independently_manipulated'])
    check('baseline_timing_correction_explicit_not_silent',p['training']['condition_specific_training_after_panas_pre'] and p['primary']['pretreatment_baseline_required'] and template['pretreatment_baseline_and_condition_training_order'] is None)
    no_leak=True
    for path in (PACKAGE/'02_仓库升级/overlay').rglob('*.md'):
        t=path.read_text();no_leak &= not any(x in t for x in ['filecite','cite','turn26file'])
    check('no_chat_ui_citation_tokens_in_overlay',no_leak)
    output=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent),pattern='test_upgrade_tools.py')
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    integrity={'status':'NOT_SEALED_YET','files':None}
    if (PACKAGE/'SHA256SUMS.txt').exists():
        try:integrity={'status':'PASS','files':verify_integrity(PACKAGE)}
        except MigrationError as exc:integrity={'status':'FAIL','reason':str(exc)}
    passed=all(x['passed'] for x in structural) and result.wasSuccessful() and integrity['status']!='FAIL'
    return {'delivery_version':'1.2','status':'PASS' if passed else 'FAIL',
            'scope':'PACKAGE_CONTRACTS_AND_SYNTHETIC_FIXTURES_ONLY',
            'structural_checks':structural,'unit_tests':{'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'log':output.getvalue()},
            'integrity':integrity,
            'not_run':['original_repository_test_suite','original_repository_patch_application','Unity','TouchDesigner','real_devices','participant_research','formal_power_simulation','institutional_approval_verification'],
            'formal_collection_allowed':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    try:report=run_validation()
    except Exception as exc:report={'status':'FAIL','reason':str(exc),'scope':'PACKAGE_VALIDATION'}
    text=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:args.output.write_text(text+'\n',encoding='utf-8')
    print(text)
    raise SystemExit(0 if report['status']=='PASS' else 1)
