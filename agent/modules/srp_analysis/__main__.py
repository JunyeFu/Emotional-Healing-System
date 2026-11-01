"""One offline entry point. No networking or experimental control."""
import argparse
from pathlib import Path

from .analyze import analyze
from .demo import make_demo
from .prepare import prepare


def main():
    parser = argparse.ArgumentParser(description='SRP read-only candidate analysis; not research admission')
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('demo', help='Create six-family synthetic data, prepare, analyze, plot and report')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--n', type=int, default=30)
    p.add_argument('--scenario', choices=['benefit', 'null', 'harm', 'floor', 'missing'], default='missing')
    p.add_argument('--power-replications', type=int, default=10)
    p.add_argument('--skip-power', action='store_true', help='Use for focused pipeline tests only')
    p = commands.add_parser('prepare', help='Read six-family bundle and create separate derived tables')
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p = commands.add_parser('analyze', help='Analyze prepared participant tables; create fixed report package')
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args.bundle, args.out)
    elif args.command == 'analyze':
        result = analyze(args.input, args.out)
    else:
        args.out.mkdir(parents=True, exist_ok=False)
        bundle = make_demo(args.out / 'originals', args.n, args.scenario)
        prepared = prepare(bundle, args.out / 'prepared')
        result = analyze(prepared, args.out / 'results')
        if not args.skip_power:
            from .power import write_power
            write_power(result, replications=args.power_replications, floor=args.scenario == 'floor')
    print(f'RESULT={result.resolve()}')
    print('SOFTWARE OUTPUT ONLY; original A/B retained; real research gates are not closed.')


if __name__ == '__main__':
    main()
