#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
from collections import defaultdict
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    args = parser.parse_args()

    rows = list(csv.DictReader(Path(args.csv_path).open(encoding="utf-8-sig")))
    if not rows:
        raise SystemExit("CSV contains no rows.")

    by_item = defaultdict(list)
    for row in rows:
        value = row.get("relevance_1_to_4", "").strip()
        if not value:
            continue
        score = int(value)
        if score not in (1, 2, 3, 4):
            raise ValueError(f"Invalid relevance score: {score}")
        by_item[row["item_id"]].append(score)

    if not by_item:
        raise SystemExit("No relevance scores entered.")

    item_cvi = {}
    for item, scores in sorted(by_item.items()):
        item_cvi[item] = sum(s >= 3 for s in scores) / len(scores)

    s_cvi_ave = sum(item_cvi.values()) / len(item_cvi)
    print("I-CVI")
    for item, value in item_cvi.items():
        print(f"{item}: {value:.3f}")
    print(f"S-CVI/Ave: {s_cvi_ave:.3f}")
    print("PASS" if all(v >= 0.78 for v in item_cvi.values()) and s_cvi_ave >= 0.90 else "REVISE")

if __name__ == "__main__":
    main()
