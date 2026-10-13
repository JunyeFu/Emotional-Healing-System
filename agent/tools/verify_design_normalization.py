"""Design-only consistency and independent synthetic arithmetic, not runtime acceptance."""
from pathlib import Path
import json
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'agent/design/design-foundation-20261008'
GOV=ROOT/'agent/governance/planning/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'

def verify():
    d=json.loads((D/'operational-design.json').read_text(encoding='utf-8'))
    norm=d['normalization']
    assert not d['formal_collection_allowed'] and not d['numeric_parameters_frozen'] and not d['runtime_api_modified']
    assert not norm['design_closed'] and {g['id'] for g in norm['open_design_gaps']}=={'M01','M02'}
    assert d['materials']['primary_measurement']['selected_form'] is None
    assert d['materials']['primary_measurement']['item_texts'] is None
    assert set(d['parameter_specs'])==set(d['pending_parameters']) and len(d['parameter_specs'])==18
    for key,s in d['parameter_specs'].items():
        for field in ['definition_and_unit','evidence_and_role','candidate_domain','data_and_determination','acceptance_rule','acceptance_basis','owner_tasks','verification_material','failure_revision']:
            assert s[field], (key,field)
        assert s['final_value'] is None and s['empirical_validation']=='NOT_EXECUTED'
        assert all((ROOT/'agent/tasks'/t/'TASK.md').exists() for t in s['owner_tasks'])
    items=d['materials']['comprehension_items']
    assert len(items)==11 and len({x['id'] for x in items})==11
    assert [sum(x['condition']==c for x in items) for c in ['COMMON','A','B']]==[4,3,4]
    for x in items:
        assert all(x[k] for k in ['prompt','construct','answer','truth','scoring','missing','validation'])
        assert x['validation_status']=='NOT_EXECUTED'
    assert len(d['scientific_matrix'])==9 and d['scientific_matrix'][-1]['review_status']=='PUBLISHER_FULLTEXT_READ'
    assert d['participants']['technical_split']['calibration']+d['participants']['technical_split']['heldout']==20
    assert 100-12-20==d['participants']['formal_if_100_students']
    assert 100-8-12-20==d['participants']['formal_if_100_people_including_experts']
    assert norm['phase_order'].index('前置实现及验证')<norm['phase_order'].index('正式参数/分析/协议冻结')
    # Independent synthetic scale calculation: not measured or selected control values.
    current,req,limit,up=.20,.60,.30,.05
    proposed=min(limit,current+min(up,max(0,req-current)))
    assert abs(proposed-.25)<1e-12 and proposed-current<=up+1e-12
    assert max(0,.02-.05)==0
    # Independent design oracle: no runtime implementation or physiology estimation.
    def design_decision(condition, valid, observed, ideal_duration, requested_scale, remaining):
        scale=0 if condition=='A' or not valid else min(.30,max(0,requested_scale))
        guide=ideal_duration*(1+scale)
        start_cycle=remaining>=guide
        accumulate=condition=='B' and valid and observed is not None and start_cycle
        return guide,start_cycle,accumulate
    assert design_decision('A',True,12,12,.30,30)==design_decision('A',True,28,12,.10,30)
    assert design_decision('A',False,None,12,.30,30)==(12,True,False)
    guide,start,accumulate=design_decision('B',True,14,12,.60,30)
    assert abs(guide-15.6)<1e-12 and start and accumulate
    assert design_decision('B',False,None,12,.30,30)==(12,True,False)
    guide,start,accumulate=design_decision('B',True,14,12,.20,8)
    assert abs(guide-14.4)<1e-12 and not start and not accumulate
    # Independently score modules separately, stop at observed duration, then aggregate time.
    modules=[{'C':4,'K':3,'U':2},{'C':2,'K':1,'U':1}]
    scored=sum(x['C'] for x in modules);T=sum(sum(x.values()) for x in modules)
    assert T==13 and scored==6 and scored/T != (4/9+2/4)/2
    # Same X must retain I deviation even when G changes; better G following can leave I worse.
    ideal=[3,3,3,3]; actual=[4,3,4,3]; guide_a=ideal; guide_b=[4,3,4,3]
    error=lambda x,y:sum(abs(a-b) for a,b in zip(x,y))
    assert error(actual,ideal)==2 and error(actual,guide_b)==0 and error(actual,guide_a)==2
    assert error(actual,ideal)==error(actual,list(ideal))
    # A two-second signal hole crosses an unjudgeable whole cycle: U is twenty, not two.
    cycles=[(0,20,True),(20,40,None),(40,60,False),(60,80,True),(80,100,False)]
    hole=(24,26)
    affected=[(a,b) for a,b,_ in cycles if a<hole[1] and b>hole[0]]
    unknown=sum(b-a for a,b in affected)
    C=sum(b-a for a,b,state in cycles if state is True)
    K=sum(b-a for a,b,state in cycles if state is False)
    assert unknown==20 and C+K+unknown==100 and 100-(hole[1]-hole[0])==98
    assert C/100==.4 and (C+unknown)/100==.6 and (C+K)/100==.8
    # No extra cycle when remaining time cannot fit a complete planned cycle.
    assert 8<sum(ideal) and 8<sum(guide_b)
    texts={}; total=0
    for p in sorted(D.glob('*.tex')):
        pdf=p.with_suffix('.pdf');assert pdf.stat().st_mtime>=p.stat().st_mtime,p
        reader=PdfReader(pdf);total+=len(reader.pages)
        texts[p.name]=''.join(page.extract_text() or '' for page in reader.pages)
        for page in reader.pages:
            names=[]
            for ref in page['/Resources']['/Font'].values():
                f=ref.get_object();names.append(str(f['/BaseFont']))
                child=f['/DescendantFonts'][0].get_object() if '/DescendantFonts' in f else f
                fd=child['/FontDescriptor'].get_object()
                assert any(k in fd for k in ['/FontFile','/FontFile2','/FontFile3'])
            assert any('SimHei' in n for n in names) or not (page.extract_text() or '').strip()
        log=ROOT/'agent/local/artifacts/task-latex-20261008/build/design-foundation-20261008'/p.with_suffix('.log').name
        content=log.read_text(encoding='utf-8',errors='replace')
        assert 'Overfull' not in content and 'Missing character' not in content,p
    assert all(key in texts['05-control-spec.tex'] for key in d['pending_parameters'])
    assert all(x['id'] in texts['07-protocol-candidate.tex'] for x in items)
    assert 'M01' in texts['03-decisions.tex'] and 'M02' in texts['03-decisions.tex']
    compact=''.join(texts['07-protocol-candidate.tex'].split())
    assert '不能仅凭目标提示确认自己的真实动作' in compact
    assert '33个直接消费者' in ''.join(texts['01-design.tex'].split())
    before=json.loads((ROOT/'agent/local/artifacts/design-normalization-20261008/before/state.json').read_text(encoding='utf-8'))
    assert (GOV/'05_可领取任务包.csv').read_text(encoding='utf-8-sig')==before['registry']
    for task in d['consumers']:
        s=json.loads((ROOT/'agent/tasks'/task/'outputs/summary.json').read_text(encoding='utf-8'))
        old=json.loads((ROOT/'agent/tasks'/task/'archive/pre-design-baseline-20261008/summary.json').read_text(encoding='utf-8-sig'))
        assert s['historical_acceptance']==old['historical_acceptance']
        assert s['normalization_candidate']==norm['id'] and not s['normalization_design_closed']
        assert any(p.startswith('NORM-20261008：') for p in s['sections'][2]['paragraphs'])
    print(f'PASS_DESIGN_ONLY: 18 specifications, 11 items, 9 source records, 7 PDFs/{total} pages, {len(d["consumers"])} handoffs; independent scale/I-G/uncertainty/budget arithmetic; M01/M02 correctly remain open')

if __name__=='__main__':verify()
