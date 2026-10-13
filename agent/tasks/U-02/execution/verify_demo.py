"""Reject empty development captures and record actual pixel measurements."""
import json
from pathlib import Path

from PIL import Image, ImageStat

PACKAGE = Path(__file__).resolve().parents[1]
DEMO = PACKAGE / 'evidence/runtime/demo'


def main():
    frames = sorted((DEMO / 'frames').glob('frame_*.png'))
    if [p.name for p in frames] != [f'frame_{i:04d}.png' for i in range(120)]:
        raise ValueError('U02_DEMO_FRAME_SET')
    measurements = []
    for path in frames:
        with Image.open(path) as image:
            gray = image.convert('L')
            spread = max(ImageStat.Stat(gray).stddev)
            low, high = gray.getextrema()
            if image.size != (960, 600) or spread < 2 or high - low < 20:
                raise ValueError(f'U02_DEMO_EMPTY_FRAME {path.name}')
            measurements.append({'frame': path.name, 'stddev': round(spread, 3),
                                 'min': low, 'max': high})
    (DEMO / 'pixel-check.json').write_text(json.dumps({
        'result': 'PASS', 'frames': 120, 'measurements': measurements,
        'scope': 'Nonblank actual Unity render; visual readability is reviewed separately'
    }, indent=2) + '\n', encoding='utf-8')
    print('PASS U02 nonblank pixel checks: 120 actual Unity frames')


if __name__ == '__main__':
    main()
