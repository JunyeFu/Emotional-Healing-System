"""Reproduce the planning anchors in the SRP implementation baseline."""

from __future__ import annotations

import json
import math
from statistics import NormalDist


def round_up(value: float, block: int) -> int:
    return math.ceil(value / block) * block


def ni_per_group(sd: float, margin: float, power: float = 0.90) -> float:
    z = NormalDist().inv_cdf(0.975) + NormalDist().inv_cdf(power)
    return 2 * z**2 * sd**2 / margin**2


def superiority_per_group(effect_size: float, power: float = 0.90) -> float:
    z = NormalDist().inv_cdf(0.975) + NormalDist().inv_cdf(power)
    return 2 * z**2 / effect_size**2


def main() -> None:
    ni_raw = ni_per_group(sd=0.15, margin=0.075)
    superiority_raw = superiority_per_group(effect_size=0.50)
    result = {
        "alpha_two_sided": 0.05,
        "power": 0.90,
        "ni": {
            "sd": 0.15,
            "margin": 0.075,
            "raw_per_group": ni_raw,
            "order_balanced_per_group": round_up(ni_raw, 24),
        },
        "superiority": {
            "effect_size": 0.50,
            "raw_per_group": superiority_raw,
            "order_balanced_per_group": round_up(superiority_raw, 24),
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
