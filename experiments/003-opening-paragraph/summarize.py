#!/usr/bin/env python3
"""Describe saved pilot measurements and select samples without model inference."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import mean, median


def summarize(directory):
    results = json.loads((directory / 'results.json').read_text())
    attempts = json.loads((directory / 'attempts.json').read_text())
    groups = defaultdict(list)
    for row in results:
        groups[(row['case'], row['variant'])].append(row)
    measurements = []
    for (case, variant), rows in sorted(groups.items()):
        stats = [row['encode'] for row in rows]
        sizes = [item['cover_bytes'] for item in stats]
        measurements.append({
            'case': case, 'variant': variant, 'completed': len(rows),
            'temperature': rows[0]['temperature'],
            'opening': rows[0]['opening'],
            'cover_bytes': sizes, 'mean_cover_bytes': mean(sizes),
            'median_cover_bytes': median(sizes),
            'mean_opening_bytes': mean(item.get('opening_bytes', 0) for item in stats),
            'mean_encode_seconds': mean(item['elapsed_seconds'] for item in stats),
            'mean_decode_seconds': mean(row['decode']['elapsed_seconds'] for row in rows),
            'mean_frame_bits_per_token': mean(item['realized_frame_bits_per_token'] for item in stats),
            'all_exact_bytes': all(row['exact_bytes'] for row in rows),
        })
    # Choose by condition and repetition, rather than by how good the output reads.
    samples = []
    for row in sorted(results, key=lambda item: item['name']):
        if row['case'] != 'paragraph' or row['repetition'] != 1:
            continue
        if row['kind'] == 'opening' and row['temperature'] != '1.0':
            continue
        if row['kind'] == 'control' and row['variant'] != 'warm-auto':
            continue
        cover_path = directory / (row['name'] + '.cover.txt')
        cover = cover_path.read_bytes()
        public, continuation = cover.split(b'\n\n', 1) if row['kind'] == 'opening' else (b'', cover)
        samples.append({
            'name': row['name'], 'cover': str(cover_path),
            'selection': 'paragraph payload, first repetition; seeded T1.0 or warm control',
            'opening': public.decode('utf-8'),
            'continuation': continuation.decode('utf-8'),
            'cover_bytes': len(cover), 'continuation_bytes': len(continuation),
            'exact_bytes': row['exact_bytes'],
        })
    return {
        'attempt_statuses': dict(Counter(item['status'] for item in attempts)),
        'completed_round_trips': len(results),
        'all_completed_exact_bytes': all(row['exact_bytes'] for row in results),
        'measurements': measurements, 'samples': samples,
        'assessment': 'Descriptive measurements only; no human ratings or detectability study.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = json.dumps(summarize(args.directory), indent=2, ensure_ascii=False) + '\n'
    if args.output:
        with args.output.open('x') as handle:
            handle.write(report)
    else:
        print(report, end='')


if __name__ == '__main__':
    main()
