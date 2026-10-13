"""Classify precomputed, correctly signed 95% CIs; does not fit a model.

All shipped examples are synthetic. No p>=.05 -> equivalence conversion,
no single-mechanism attribution, no automated deployment/ethics approval.
"""
from __future__ import annotations
import argparse
import json
import math
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Evidence:
    estimate: float
    ci_low: float
    ci_high: float
    practical_delta: float | None = None
    ci_level: float = 0.95
    affect_assessable: bool = True
    delivery_valid: bool = True
    functional_guard: str = 'UNKNOWN'  # PASS, FAIL, UNKNOWN
    sensitivity: str = 'UNKNOWN'      # ROBUST, SENSITIVE, UNKNOWN

def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a finite number, not a boolean.')
    if not math.isfinite(value):
        raise ValueError(f'{name} must be finite.')
    return float(value)

def classify(e: Evidence) -> dict[str, Any]:
    est=_number(e.estimate,'estimate'); lo=_number(e.ci_low,'ci_low'); hi=_number(e.ci_high,'ci_high')
    level=_number(e.ci_level,'ci_level')
    if level != 0.95:
        raise ValueError('v1.2 classifier requires a 95% CI; do not pass a TOST 90% CI.')
    if not lo < hi or not lo <= est <= hi:
        raise ValueError('Require ci_low < ci_high and estimate inside its CI.')
    if type(e.affect_assessable) is not bool or type(e.delivery_valid) is not bool:
        raise ValueError('Evidence flags must be explicit booleans.')
    if e.functional_guard not in {'PASS','FAIL','UNKNOWN'}:
        raise ValueError('Unknown functional_guard.')
    if e.sensitivity not in {'ROBUST','SENSITIVE','UNKNOWN'}:
        raise ValueError('Unknown sensitivity status.')
    d=None if e.practical_delta is None else _number(e.practical_delta,'practical_delta')
    if d is not None and d <= 0:
        raise ValueError('A prespecified practical_delta must be >0.')
    if not e.affect_assessable:
        direction='NOT_ASSESSABLE'; practical='NOT_ASSESSABLE'
    else:
        direction='NATIVE_LOWER' if hi < 0 else 'ABSTRACT_LOWER' if lo > 0 else 'NO_DIRECTION_ESTABLISHED'
        if d is None: practical='THRESHOLD_NOT_FROZEN'
        elif hi < -d: practical='NATIVE_IMPORTANT_BENEFIT_SUPPORTED'
        elif lo > d: practical='ABSTRACT_IMPORTANT_BENEFIT_SUPPORTED'
        elif lo > -d and hi < d: practical='WITHIN_PRESPECIFIED_PRACTICAL_BOUNDS'
        else: practical='IMPORTANT_EFFECT_NOT_EXCLUDED'
    return {
        'input':{'estimate':est,'ci95':[lo,hi],'practical_delta':d},
        'contrast':'native_minus_abstract; lower_negative_affect_is_better',
        'direction_evidence':direction,'practical_scale':practical,
        'interpretation_scope':'ASSIGNED_IMPLEMENTATIONS' if e.delivery_valid else 'DELIVERY_VALIDITY_LIMITED',
        'functional_guard':e.functional_guard,'sensitivity':e.sensitivity,
        'prespecified_affect_result_must_be_reported':True,
        'formal_equivalence_claim_allowed':False,
        'automatic_deployment_recommendation':False,
        'mechanism_or_all_explicit_vs_native_claim_allowed':False,
        'long_term_or_treatment_efficacy_claim_allowed':False,
        'note':'CI classification is not formal SAP execution. Functional failure does not hide affect results. Equivalence requires separately prespecified methods and margins; default is disabled.'
    }

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input_json',help='JSON containing Evidence fields, using a 95% CI.')
    args=p.parse_args()
    try:
        with open(args.input_json,encoding='utf-8-sig') as f: obj=json.load(f)
        result=classify(Evidence(**obj))
    except (OSError,ValueError,TypeError,json.JSONDecodeError) as exc:
        p.exit(2,f'Input rejected: {exc}\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
