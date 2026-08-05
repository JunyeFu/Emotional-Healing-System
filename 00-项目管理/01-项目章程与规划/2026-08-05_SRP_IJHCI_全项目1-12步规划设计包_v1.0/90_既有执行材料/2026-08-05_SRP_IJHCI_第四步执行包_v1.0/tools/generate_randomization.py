#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

SEQUENCES = {
    "W1": ["storm", "heat", "fade", "snow"],
    "W2": ["heat", "snow", "storm", "fade"],
    "W3": ["snow", "fade", "heat", "storm"],
    "W4": ["fade", "storm", "snow", "heat"],
}
CONDITION_ORDERS = {
    "SN_AP": ["scene_native", "abstract_pacer"],
    "AP_SN": ["abstract_pacer", "scene_native"],
}


def build_schedule(n: int, seed: int) -> list[dict[str, object]]:
    if n <= 0 or n % 8 != 0:
        raise ValueError("n must be a positive multiple of 8.")
    cells = [(order, seq) for order in CONDITION_ORDERS for seq in SEQUENCES]
    assignments = cells * (n // len(cells))
    rng = random.Random(seed)
    rng.shuffle(assignments)

    rows = []
    for idx, (order_code, seq_code) in enumerate(assignments, start=1):
        pid = f"P{idx:04d}"
        modes = CONDITION_ORDERS[order_code]
        rows.append({
            "participant_id": pid,
            "condition_order_code": order_code,
            "williams_sequence_code": seq_code,
            "session1_cue_mode": modes[0],
            "session2_cue_mode": modes[1],
            "module_sequence": "|".join(SEQUENCES[seq_code]),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=104)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-dir", default="allocation")
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = build_schedule(args.n, args.seed)

    schedule_path = out / "allocation_schedule.csv"
    with schedule_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    seed_hash = hashlib.sha256(str(args.seed).encode()).hexdigest()
    metadata = {
        "randomization_version": "1.0.0",
        "n": args.n,
        "seed_sha256": seed_hash,
        "cells": 8,
        "participants_per_cell": args.n // 8,
        "williams_sequences": SEQUENCES,
        "condition_orders": CONDITION_ORDERS,
    }
    (out / "allocation_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(schedule_path)
    print(out / "allocation_metadata.json")


if __name__ == "__main__":
    main()
