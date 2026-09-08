"""Planning approximations only; no participant data or final power simulation."""
from __future__ import annotations
import json
import math
from statistics import NormalDist

def rounded(value: float, block: int) -> int:
    if not math.isfinite(value) or value<=0 or type(block) is not int or block<=0:
        raise ValueError('Positive finite value and integer block required.')
    return block*math.ceil(value/block)

def planning_results() -> dict:
    z=NormalDist().inv_cdf(.975)+NormalDist().inv_cdf(.90)
    out=[]
    for d in [.2,.3,.4,.5,.6]:
        per_arm=math.ceil(2*z*z/(d*d))
        complete_anchor=rounded(2*per_arm,48)
        out.append({'residual_standardized_difference':d,'ideal_n_per_arm':per_arm,
                    'complete_results_rounded_for_planning':complete_anchor,
                    'illustrative_recruitment_with_20pct_unavailable':rounded(complete_anchor/.8,48)})
    return {
        'evidence_status':'ANALYTIC_APPROXIMATIONS_NOT_OBSERVED_DATA_NOT_FORMAL_MONTE_CARLO',
        'formula':'n_per_arm=ceil(2*(z_.975+z_.90)^2/d_residual^2)',
        'alpha_two_sided':.05,'target_power':.90,
        'warning':'d is difference / ANCOVA residual SD, not raw-score Cohen d. 20% unavailability is illustrative, inferred from the old 192/240 anchor, not observed. Actual N/stopping must be frozen for assigned participants; never refill outcome cells.',
        'affect_sensitivity':out,
        'capacity':{
            'core_sessions_anchor':288,'core_station_hours':[288*55/60,288*70/60],
            'full_sessions_anchor':528,'full_station_hours':[528*55/60,528*70/60],
            'illustrative_sessions_per_week':32,'core_collection_weeks':288/32,'full_collection_weeks':528/32,
            'excludes':'Level A/B, extra rehearsal, approvals, scheduling, no-shows, failures, analysis, staffing overhead'},
        'pf_counterexample':{'module_differences':[-.24,0,0,0],'mean':-.06,'candidate_margin':.075,
                            'conclusion':'Mean contrast within the margin does not establish each module noninferior.'},
        'formal_collection_allowed':False
    }

if __name__=='__main__':print(json.dumps(planning_results(),ensure_ascii=False,indent=2))
