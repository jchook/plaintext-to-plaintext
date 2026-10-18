#!/usr/bin/env python3
"""Run real model round trips in separate encoder and decoder processes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path,
                        default=root / 'runs' / time.strftime('%Y%m%d-%H%M%S'))
    parser.add_argument('--url', default='http://127.0.0.1:11535')
    parser.add_argument('--key', type=Path, default=root / 'keys/alice.txt')
    parser.add_argument('--cases', nargs='+',
                        choices=['key-message', 'belfry', 'unicode', 'empty'],
                        default=['key-message', 'belfry', 'unicode', 'empty'])
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=False)
    samples = {
        'key-message': b'The key is 12345',
        'belfry': b'The enemy planted a bomb in the belfry -- be CAREFUL!',
        'unicode': '  Caf\u00e9 \u2615\n\u4f60\u597d\uff0c\u4e16\u754c\u3002\nTabs:\tA\tB\r\n'.encode(),
        'empty': b'',
    }
    results = []
    for name in args.cases:
        original = args.directory / f'{name}.txt'
        cover = args.directory / f'{name}.cover.txt'
        recovered = args.directory / f'{name}.recovered.txt'
        original.write_bytes(samples[name])
        for operation, source, target in [('encode', original, cover), ('decode', cover, recovered)]:
            command = [sys.executable, str(root / 'p2p.py'), operation,
                       '--url', args.url, '--key', str(args.key),
                       '--input', str(source), '--output', str(target),
                       '--stats', str(args.directory / f'{name}.{operation}.json')]
            subprocess.run(command, check=True)
        actual = recovered.read_bytes()
        if actual != samples[name]:
            raise RuntimeError(f'Byte mismatch: {name}')
        result = {
            'case': name, 'exact_bytes': True,
            'input_sha256': hashlib.sha256(samples[name]).hexdigest(),
            'recovered_sha256': hashlib.sha256(actual).hexdigest(),
            'encode': json.loads((args.directory / f'{name}.encode.json').read_text()),
            'decode': json.loads((args.directory / f'{name}.decode.json').read_text()),
        }
        results.append(result)
        (args.directory / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(f'PASS {name}: exact {len(actual)}-byte recovery', flush=True)
    print(f'Results: {args.directory}')


if __name__ == '__main__':
    main()
