#!/usr/bin/env python3
"""Account for saved opening-pilot bytes; no inference or network access."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'experiments/003-opening-paragraph/runs/pilot-20261021'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def summarize(rows):
    fields = [
        'plaintext_bytes', 'packed_source_bytes', 'frame_bytes', 'opening_bytes',
        'separator_bytes', 'payload_cover_bytes', 'suffix_bytes', 'cover_bytes',
        'payload_tokens', 'average_top_probability_mass',
        'average_retained_probability_mass', 'average_top_entropy_bits',
        'average_selected_entropy_bits', 'average_table_entropy_bits',
        'realized_frame_bits_per_token', 'expected_entropy_bits_per_byte',
        'interval_information_bits', 'framing_overhead_bytes',
    ]
    total_tokens = sum(r['payload_tokens'] for r in rows)
    frame_bits = sum(8 * r['frame_bytes'] for r in rows)
    return {
        'n': len(rows),
        'cover_byte_range': [min(r['cover_bytes'] for r in rows),
                             max(r['cover_bytes'] for r in rows)],
        'means': {k: statistics.mean(r[k] for r in rows) for k in fields},
        # Weight per-step entropy by the number of steps, not by message count.
        'pooled_frame_bits_per_payload_token': frame_bits / total_tokens,
        'pooled_table_entropy_bits_per_payload_token': sum(
            r['average_table_entropy_bits'] * r['payload_tokens'] for r in rows
        ) / total_tokens,
        'pooled_packed_source_bits_per_full_cover_byte': sum(
            8 * r['packed_source_bytes'] for r in rows
        ) / sum(r['cover_bytes'] for r in rows),
    }


def audit():
    results_file = RUN / 'results.json'
    metadata_file = RUN / 'metadata.json'
    records = json.loads(results_file.read_text())
    metadata = json.loads(metadata_file.read_text())
    inputs = {str(p.relative_to(ROOT)): sha(p.read_bytes())
              for p in [results_file, metadata_file]}
    source_file = Path(__file__).with_name('sources.json')
    download_file = source_file.parent / 'sources/downloads.json'
    for path in [source_file, download_file]:
        inputs[str(path.relative_to(ROOT))] = sha(path.read_bytes())
    source_hashes_checked = 0
    for source in json.loads(source_file.read_text())['sources']:
        for relative, expected in source['artifact_sha256'].items():
            require(sha((ROOT / relative).read_bytes()) == expected,
                    f'Research source hash differs: {relative}')
            source_hashes_checked += 1
    for download in json.loads(download_file.read_text()):
        path = download_file.parent / (download['id'] + '.pdf')
        require(path.stat().st_size == download['pdf_bytes'] and
                sha(path.read_bytes()) == download['pdf_sha256'],
                f'Downloaded PDF differs: {path.name}')
        require(sha(path.with_suffix('.txt').read_bytes()) == download['text_sha256'],
                f'Extracted text differs: {path.name}')
    rows = []
    for record in records:
        name = record['name']
        files = {suffix: RUN / (name + suffix)
                 for suffix in ['.input', '.cover.txt', '.recovered']}
        data, cover, recovered = [files[k].read_bytes()
                                  for k in ['.input', '.cover.txt', '.recovered']]
        for path in files.values():
            inputs[str(path.relative_to(ROOT))] = sha(path.read_bytes())
        stats = record['encode']
        require(data == recovered, f'{name}: recovered bytes differ')
        require(sha(data) == record['sha256'] == record['recovered_sha256'],
                f'{name}: source hash differs')
        require(sha(cover) == record['cover_sha256'], f'{name}: cover hash differs')
        require(record['exact_bytes'] and record['decode']['authenticated'],
                f'{name}: unauthenticated or inexact result')
        require(len(data) == stats['plaintext_bytes'], f'{name}: source size differs')
        require(len(cover) == stats['cover_bytes'], f'{name}: cover size differs')
        opening_bytes = stats.get('opening_bytes', 0)
        separator_bytes = stats.get('separator_bytes', 0)
        require(len(cover) == opening_bytes + separator_bytes +
                stats['payload_cover_bytes'] + stats['suffix_bytes'],
                f'{name}: byte components do not sum to cover size')
        if record['kind'] == 'opening':
            require(cover[:opening_bytes] == stats['opening'].encode('utf-8') and
                    cover[opening_bytes:opening_bytes + separator_bytes] == b'\n\n',
                    f'{name}: public opening or separator differs')
        overhead = stats['frame_bytes'] - stats['packed_source_bytes']
        require(overhead == 30, f'{name}: unexpected frame overhead')
        fields = ['plaintext_bytes', 'packed_source_bytes', 'frame_bytes',
                  'payload_cover_bytes', 'suffix_bytes', 'cover_bytes',
                  'payload_tokens', 'average_top_probability_mass',
                  'average_retained_probability_mass', 'average_top_entropy_bits',
                  'average_selected_entropy_bits', 'average_table_entropy_bits',
                  'realized_frame_bits_per_token', 'expected_entropy_bits_per_byte',
                  'interval_information_bits']
        rows.append({
            'name': name, 'case': record['case'], 'kind': record['kind'],
            'variant': record['variant'], 'temperature': record['temperature'],
            **{k: stats[k] for k in fields},
            'opening_bytes': opening_bytes, 'separator_bytes': separator_bytes,
            'framing_overhead_bytes': overhead,
        })
    require(len(rows) == 32, 'Expected the completed 32-trial pilot')
    groups = []
    for case in sorted({r['case'] for r in rows}):
        for temperature in ['1.0', '1.2']:
            subset = [r for r in rows if r['case'] == case and
                      r['temperature'] == temperature and r['kind'] == 'opening']
            groups.append({'case': case, 'kind': 'opening',
                           'temperature': temperature, **summarize(subset)})
    return {
        'scope': 'Retrospective byte accounting; no new generation or detection measurements.',
        'pilot_source_commit': metadata['commit'],
        'checked_round_trips': len(rows),
        'checked_research_source_hashes': source_hashes_checked,
        'input_sha256': inputs,
        'opening_groups': groups,
        'trials': rows,
        'cautions': [
            'Each opening group pools three fixtures with two repetitions per fixture.',
            'Entropy diagnostics describe the sampled histories and top-64 candidate support.',
            'A finite realized rate can exceed average entropy through sampling variation.',
            'Full-vocabulary entropy, divergence, and detectability were not measured.',
        ],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Compare with saved audit.json.')
    args = parser.parse_args()
    result = audit()
    if args.check:
        saved = Path(__file__).with_name('audit.json')
        require(result == json.loads(saved.read_text()), 'Saved audit.json differs')
        print(f'PASS: {result["checked_round_trips"]} authenticated saved round trips; accounting matches.')
    else:
        print(json.dumps(result, indent=2))
