#!/usr/bin/env python3
"""Measure compact-codec variants with separate encoder and decoder processes."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time

import p2p

CASES = {
    'key-message': b'The key is 12345',
    'belfry': b'The enemy planted a bomb in the belfry -- be CAREFUL!',
    'paragraph': (b'Please meet me at the station tomorrow morning. I will be waiting near the '
                  b'ticket office at half past nine. Bring the blue notebook and leave the package '
                  b'at home. If the train is delayed, send me a message and I will wait inside the cafe.'),
    'unicode': '  Café ☕\n你好，世界。\nTabs:\tA\tB\r\n'.encode(),
    'binary': random.Random(20261019).randbytes(64),
    'empty': b'',
}
VARIANTS = {
    'legacy': None,
    'journal-raw': ('journal', 'raw'),
    'varied-raw': ('varied', 'raw'),
    'warm-raw': ('warm', 'raw'),
    'warm-auto': ('warm', 'auto'),
}


def main():
    code_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path,
                        default=code_root.parent / 'experiments' / '002-compact-v2' / 'runs' /
                        time.strftime('%Y%m%d-%H%M%S'))
    parser.add_argument('--key', type=Path, default=code_root / 'keys/alice.txt')
    parser.add_argument('--url', default=p2p.DEFAULT_URL)
    parser.add_argument('--variants', choices=VARIANTS, nargs='+', default=['warm-auto'])
    parser.add_argument('--cases', choices=CASES, nargs='+', default=list(CASES))
    parser.add_argument('--repetitions', type=int, default=1)
    parser.add_argument('--max-tokens', type=int, default=5000)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error('--repetitions must be positive')
    root = Path(args.directory)
    root.mkdir(parents=True, exist_ok=False)
    results = []
    for case in args.cases:
        for variant in args.variants:
            for repetition in range(1, args.repetitions + 1):
                name = f'{case}.{variant}.{repetition}'
                print(f'Starting {name}', flush=True)
                data = CASES[case]
                original = root / f'{name}.input'
                original.write_bytes(data)
                cover = root / f'{name}.cover.txt'
                recovered = root / f'{name}.recovered'
                profile = VARIANTS[variant]
                script = 'p2p.py' if profile is None else 'compact.py'
                base = [sys.executable, str(code_root / script)]
                common = ['--key', str(args.key), '--url', args.url, '--max-tokens', str(args.max_tokens)]
                if profile:
                    common += ['--profile', profile[0], '--compression', profile[1]]
                stats = {}
                for action, source, destination in (('encode', original, cover), ('decode', cover, recovered)):
                    stats_file = root / f'{name}.{action}.json'
                    with (root / f'{name}.{action}.log').open('w') as log:
                        subprocess.run(base + [action] + common + ['--input', str(source), '--output',
                                       str(destination), '--stats', str(stats_file)],
                                       stdout=log, stderr=log, check=True)
                    stats[action] = json.loads(stats_file.read_text())
                restored = recovered.read_bytes()
                if restored != data:
                    raise RuntimeError(f'Exact byte comparison failed for {name}')
                result = {'name': name, 'case': case, 'variant': variant, 'repetition': repetition,
                          'exact_bytes': True, 'sha256': hashlib.sha256(data).hexdigest(),
                          'recovered_sha256': hashlib.sha256(restored).hexdigest(), **stats}
                results.append(result)
                (root / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
                print(json.dumps({'name': name, 'exact_bytes': True, 'plaintext_bytes': len(data),
                                  'cover_bytes': stats['encode']['cover_bytes'],
                                  'frame_bytes': stats['encode']['frame_bytes'],
                                  'compression': stats['encode'].get('compression', 'raw'),
                                  'encode_seconds': stats['encode']['elapsed_seconds']}), flush=True)


if __name__ == '__main__':
    main()
