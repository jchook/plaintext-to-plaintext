#!/usr/bin/env python3
"""Create immutable randomized blind-review batches; mapping stays separate."""
from pathlib import Path
import argparse
import hashlib
import json
import random

ROOT = Path(__file__).resolve().parent
DIMENSIONS = ['fluency', 'coherence_purpose', 'sender_recipient', 'unsupported_claims',
              'repetition', 'ending', 'length']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, default=ROOT/'runs/pilot-20261022')
    p.add_argument('--batch-size', type=int, default=10)
    args = p.parse_args()
    review = args.run/'blind-review'
    review.mkdir(exist_ok=True)
    mapping_path = args.run/'blind-mapping.json'
    if not mapping_path.exists():
        attempts = json.loads((args.run/'attempts.json').read_text())
        names = sorted(a['name'] for a in attempts)
        random.Random(93261022).shuffle(names)
        mapping = {name: hashlib.sha256(f'opaque-93261022-{i}'.encode()).hexdigest()[:12]
                   for i, name in enumerate(names)}
        mapping_path.write_text(json.dumps(mapping, indent=2)+'\n')
    mapping = json.loads(mapping_path.read_text())
    used = set()
    for batch in review.glob('batch-*.json'):
        used.update(r['id'] for r in json.loads(batch.read_text())['samples'])
    results = json.loads((args.run/'results.json').read_text())
    new = [r for r in results if mapping[r['name']] not in used]
    attempts = json.loads((args.run/'attempts.json').read_text())
    finished = all(a['status'] in ('success', 'failed', 'interrupted') for a in attempts)
    if len(new) < args.batch_size and not finished:
        print(f'{len(new)} new completed covers; waiting for batch of {args.batch_size}')
        return
    random.Random(53261022 + len(used)).shuffle(new)
    if not finished:
        new = new[:args.batch_size]
    rows = []
    for row in new:
        cover = (args.run/(row['name']+'.cover.txt')).read_text()
        opening, continuation = cover.split('\n\n',1)
        rows.append({'id': mapping[row['name']], 'opening': opening, 'continuation': continuation})
    if not rows:
        return
    number = len(list(review.glob('batch-*.json')))+1
    target = review/f'batch-{number:02}.json'
    target.write_text(json.dumps({'assessment':'blinded machine assessment; no human ratings',
                                 'dimensions': DIMENSIONS, 'scale':'0=clear failure, 1=noticeable weakness, 2=acceptable',
                                 'acceptance':'sum>=11 and fluency/coherence_purpose/sender_recipient all>=1',
                                 'samples':rows},indent=2,ensure_ascii=False)+'\n')
    print(target)


if __name__ == '__main__':
    main()
