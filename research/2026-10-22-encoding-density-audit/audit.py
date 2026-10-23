#!/usr/bin/env python3
"""Retrospective size and prose-structure accounting; no model inference."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit():
    hashes, rows = {}, []

    def read(path):
        data = path.read_bytes()
        hashes[str(path.relative_to(ROOT))] = sha(data)
        return data

    def add(directory, name, stats, case, group, record=None, legacy=False):
        source = read(directory / (name + ('.txt' if legacy else '.input')))
        cover = read(directory / (name + '.cover.txt'))
        recovered = read(directory / (name + ('.recovered.txt' if legacy else '.recovered')))
        assert source == recovered
        assert len(cover) == stats['cover_bytes']
        if record:
            assert record['exact_bytes'] and record['decode']['authenticated']
            assert sha(source) == record['sha256'] == record['recovered_sha256']
            if 'cover_sha256' in record:
                assert sha(cover) == record['cover_sha256']
        opening = stats.get('opening_bytes', 0)
        separator = stats.get('separator_bytes', 0)
        payload_bytes = stats.get('payload_cover_bytes')
        suffix = stats.get('suffix_bytes')
        start = opening + separator
        continuation = cover[start:].decode('utf-8')
        if payload_bytes is not None:
            assert start + payload_bytes + suffix == len(cover)
        frame = stats['frame_bytes']
        packed = stats.get('packed_source_bytes')
        row = {
            'cover_path': str((directory / (name + '.cover.txt')).relative_to(ROOT)),
            'name': name, 'group': group, 'case': case,
            'input_bytes': len(source), 'packed_source_bytes': packed,
            'frame_bytes': frame, 'cover_bytes': len(cover),
            'public_opening_separator_bytes': start,
            'payload_cover_bytes': payload_bytes, 'suffix_bytes': suffix,
            'payload_tokens': stats['payload_tokens'],
            'original_input_bits_per_complete_byte': 8 * len(source) / len(cover),
            'packed_source_bits_per_complete_byte': 8 * packed / len(cover) if packed else None,
            'frame_bits_per_carrying_byte': 8 * frame / payload_bytes if payload_bytes else None,
            'carrying_bytes_per_token': payload_bytes / stats['payload_tokens'] if payload_bytes else None,
            'frame_bits_per_payload_token': 8 * frame / stats['payload_tokens'],
            'table_entropy_bits_per_payload_token': stats.get('average_table_entropy_bits'),
            'entropy_per_expected_visible_byte': stats.get('expected_entropy_bits_per_byte'),
            'interval_overshoot_bits': stats['interval_information_bits'] - 8 * frame
                if 'interval_information_bits' in stats else None,
            'continuation_paragraphs': len(re.split(r'\n\s*\n', continuation.strip())),
            'continuation_question_marks': continuation.count('?'),
            # A descriptive substring count, not a semantic judgment of repetition.
            'continuation_think_occurrences': len(re.findall(r'\bthink\b', continuation, re.I)),
            'temperature': record.get('temperature') if record else None,
        }
        rows.append(row)

    base = ROOT / 'experiments/001-baseline-v1'
    stats = json.loads(read(base / 'examples/key-message.encode.json'))
    add(base / 'examples', 'key-message', stats, 'key-message', 'v1', legacy=True)
    directory = base / 'runs/verified'
    for record in json.loads(read(directory / 'results.json')):
        add(directory, record['case'], record['encode'], record['case'], 'v1', legacy=True)

    for group in ['main', 'edge-cases', 'ablation', 'paragraph-baseline']:
        directory = ROOT / 'experiments/002-compact-v2/runs' / group
        for record in json.loads(read(directory / 'results.json')):
            add(directory, record['name'], record['encode'], record['case'], 'compact-' + group,
                record=record)
    directory = ROOT / 'experiments/003-opening-paragraph/runs/pilot-20261021'
    for record in json.loads(read(directory / 'results.json')):
        add(directory, record['name'], record['encode'], record['case'],
            'opening' if record['kind'] == 'opening' else 'opening-control', record=record)
    assert len(rows) == 57

    groups = []
    for case in ['key-message', 'paragraph']:
        for temp in ['1.0', '1.2']:
            selected = [r for r in rows if r['group'] == 'opening' and
                        r['case'] == case and r['temperature'] == temp]
            carrying = sum(r['payload_cover_bytes'] for r in selected)
            frame = sum(r['frame_bytes'] for r in selected)
            packed = sum(r['packed_source_bytes'] for r in selected)
            total = sum(r['cover_bytes'] for r in selected)
            # Constant-rate accounting allocation; not a re-encoding prediction.
            overhead = frame - packed
            per_frame_byte = carrying / frame
            groups.append({
                'case': case, 'temperature': temp, 'n': len(selected),
                'mean_cover_bytes': total / len(selected),
                'mean_carrying_bytes': carrying / len(selected),
                'mean_opening_separator_bytes': statistics.mean(
                    r['public_opening_separator_bytes'] for r in selected),
                'mean_suffix_bytes': statistics.mean(r['suffix_bytes'] for r in selected),
                'pooled_frame_bits_per_carrying_byte': 8 * frame / carrying,
                'pooled_packed_source_bits_per_complete_byte': 8 * packed / total,
                'pooled_original_input_bits_per_complete_byte':
                    8 * sum(r['input_bytes'] for r in selected) / total,
                'mean_visible_allocation_outer_frame_overhead':
                    per_frame_byte * overhead / len(selected),
                'mean_visible_allocation_packed_source': per_frame_byte * packed / len(selected),
                'mean_visible_allocation_16B_digest':
                    per_frame_byte * 16 if case == 'paragraph' else 0,
                'carrying_byte_range': [min(r['payload_cover_bytes'] for r in selected),
                                        max(r['payload_cover_bytes'] for r in selected)],
                'frame_bits_per_token_range': [min(r['frame_bits_per_payload_token'] for r in selected),
                                              max(r['frame_bits_per_payload_token'] for r in selected)],
                'mean_continuation_paragraphs': statistics.mean(
                    r['continuation_paragraphs'] for r in selected),
                'mean_continuation_question_marks': statistics.mean(
                    r['continuation_question_marks'] for r in selected),
            })
    close_examples = []
    for name, phrase in [
        ('paragraph.opening-history-revision-t1.0.1', 'Let me know'),
        ('paragraph.opening-conference-followup-t1.0.2', 'So far, the feedback'),
    ]:
        row = next(r for r in rows if r['group'] == 'opening' and r['name'] == name)
        cover = (ROOT / row['cover_path']).read_bytes()
        at = cover.index(phrase.encode())
        end = cover.find(b'\n\n', at) + 2
        assert end > 1
        payload_end = row['public_opening_separator_bytes'] + row['payload_cover_bytes']
        close_examples.append({
            'name': name, 'boundary': 'After paragraph beginning ' + repr(phrase),
            'following_visible_bytes': len(cover) - end,
            'following_carrying_bytes': max(0, payload_end - end),
            'suffix_bytes': row['suffix_bytes'],
        })
    return {
        'scope': '57 archived successful encodings; retrospective accounting only.',
        'method': 'Original input bits are representation length, not measured source entropy. '
                  'Frame overhead allocation assumes constant observed carrying rate and is not a '
                  'prediction after changing the frame. Paragraph and punctuation counts are descriptive.',
        'checked_round_trips': len(rows), 'input_sha256': hashes,
        'opening_groups': groups, 'selected_close_examples': close_examples, 'trials': rows,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = audit()
    if args.check:
        assert result == json.loads((HERE / 'audit.json').read_text())
        print('PASS: 57 saved exact byte comparisons; density accounting matches.')
    else:
        print(json.dumps(result, indent=2))
