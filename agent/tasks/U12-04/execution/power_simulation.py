"""Current raw-point precision wrapper; original implementation is archived."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'agent/modules'))
from srp_analysis.power import run_power_grid
from srp_analysis.io import write_json, save_frame
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--replications', type=int, default=10)
    parser.add_argument('--n-total', type=int)
    parser.add_argument('--effect-points', type=float)
    parser.add_argument('--missing-post-rate', type=float)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError('OUTPUT_DIRECTORY_EXISTS')
    kwargs = {'replications': args.replications}
    for argument, key in [('n_total', 'n_grid'), ('effect_points', 'effect_grid'), ('missing_post_rate', 'missing_rates')]:
        value = getattr(args, argument)
        if value is not None:
            kwargs[key] = (value,)
    result = run_power_grid(**kwargs)
    args.output_dir.mkdir(parents=True)
    write_json(args.output_dir / 'power_grid.json', result)
    save_frame(args.output_dir / 'power_grid.csv', pd.DataFrame(result['cells']))
    print('SYNTHETIC precision output; formal N remains unfrozen.')


if __name__ == '__main__':
    main()
