#!/usr/bin/env python3
"""Check the organized archive without model inference or network access."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    migration = json.loads((ROOT / 'experiments/migration.json').read_text())
    errors = []
    counts = {}

    def require(condition, message):
        if not condition:
            errors.append(message)

    def check_hash(path, expected):
        require(path.is_file(), f'Missing artifact: {path.relative_to(ROOT)}')
        if path.is_file():
            require(digest(path.read_bytes()) == expected,
                    f'Hash mismatch: {path.relative_to(ROOT)}')

    def current_path(original):
        for old, new in migration['path_aliases'].items():
            if original == old or original.startswith(old + '/'):
                return ROOT / (new + original[len(old):])
        return ROOT / original

    for entry in migration['moved_artifacts']:
        check_hash(ROOT / entry['path'], entry['sha256'])
    counts['unchanged moved artifacts'] = len(migration['moved_artifacts'])

    compact = json.loads((ROOT / 'experiments/002-compact-v2/verification.json').read_text())
    for original, expected in compact['artifact_sha256'].items():
        check_hash(current_path(original), expected)
    counts['historical compact artifact hashes'] = len(compact['artifact_sha256'])

    revision = migration['source_commit']
    for name, expected in compact['code_sha256'].items():
        saved = subprocess.run(['git', 'show', f'{revision}:poc/{name}'], cwd=ROOT,
                               capture_output=True, check=False)
        require(saved.returncode == 0, f'Cannot read source {revision}:poc/{name}')
        if saved.returncode == 0:
            require(digest(saved.stdout) == expected, f'Historical code hash mismatch: {name}')
    counts[f'historical code hashes at {revision}'] = len(compact['code_sha256'])

    opening_record = ROOT / 'experiments/003-opening-paragraph/verification.json'
    if opening_record.is_file():
        opening = json.loads(opening_record.read_text())
        for path, expected in opening['artifact_sha256'].items():
            check_hash(ROOT / path, expected)
        counts['opening pilot artifact hashes'] = len(opening['artifact_sha256'])
        source_revision = opening['source_commit']
        for path, expected in opening['code_sha256'].items():
            saved = subprocess.run(['git', 'show', f'{source_revision}:{path}'], cwd=ROOT,
                                   capture_output=True, check=False)
            require(saved.returncode == 0, f'Cannot read source {source_revision}:{path}')
            if saved.returncode == 0:
                require(digest(saved.stdout) == expected, f'Opening source hash mismatch: {path}')
        counts[f'opening code hashes at {source_revision[:7]}'] = len(opening['code_sha256'])
        validated = 0
        for path in opening.get('validation_records', []):
            for check in json.loads((ROOT / path).read_text()):
                require(check.get('passed') is True, f'Opening validation failed: {check["case"]}')
                output = (ROOT / path).parent / check['case'] / 'decoded.bin'
                if check['expected_rejection']:
                    require(check['returncode'] == 1 and not output.exists(),
                            f'Opening rejection wrote output or exited unexpectedly: {check["case"]}')
                    require(check['classification'] in check['expected_error_categories'],
                            f'Unrecognized rejection: {check["case"]}')
                else:
                    expected = output.with_name('expected.input')
                    require(output.is_file() and output.read_bytes() == expected.read_bytes(),
                            f'Opening restart bytes differ: {check["case"]}')
                    stats = json.loads(output.with_name('decode.json').read_text())
                    require(stats.get('authenticated') is True,
                            f'Opening restart unauthenticated: {check["case"]}')
                validated += 1
        counts['opening rejection/restart records checked offline'] = validated

    # Check complete triples, not just the equality flags in saved JSON.
    pairs = 0
    result_files = [ROOT / 'experiments/001-baseline-v1/verification.json']
    result_files += sorted((ROOT / 'experiments').glob('*/runs/*/results.json'))
    for result_file in result_files:
        document = json.loads(result_file.read_text())
        records = document['roundtrips'] if isinstance(document, dict) else document
        for record in records:
            if 'encode' not in record:
                continue
            name = record.get('name', record['case'])
            if result_file.name == 'verification.json':
                # The other v1 cases are checked from their own run directory.
                if name != 'key-message':
                    continue
                directory = result_file.parent / 'examples'
            else:
                directory = result_file.parent
            is_compact = 'variant' in record
            original = directory / (name + ('.input' if is_compact else '.txt'))
            restored = directory / (name + ('.recovered' if is_compact else '.recovered.txt'))
            cover = directory / (name + '.cover.txt')
            if not all(p.is_file() for p in (original, restored, cover)):
                errors.append(f'Incomplete round trip: {directory.relative_to(ROOT)}/{name}')
                continue
            data = original.read_bytes()
            require(restored.read_bytes() == data, f'Recovered byte mismatch: {restored}')
            require(digest(data) == record.get('sha256', record.get('input_sha256')),
                    f'Input digest mismatch: {original}')
            require(digest(restored.read_bytes()) == record['recovered_sha256'],
                    f'Recovered digest mismatch: {restored}')
            for phase in ('encode', 'decode'):
                require(record[phase]['plaintext_bytes'] == len(data),
                        f'Plaintext size mismatch: {name}/{phase}')
                require(record[phase]['cover_bytes'] == cover.stat().st_size,
                        f'Cover size mismatch: {name}/{phase}')
            require(record['exact_bytes'] and record['decode']['authenticated'],
                    f'Round trip not recorded as authenticated and exact: {name}')
            pairs += 1
    counts['saved full round trips compared byte-for-byte'] = pairs

    restart_root = ROOT / 'experiments/002-compact-v2/runs/restart'
    restarts = json.loads((restart_root / 'results.json').read_text())
    for record in restarts:
        original = current_path(record['original'])
        restored = restart_root / (record['case'] + '.recovered')
        require(original.read_bytes() == restored.read_bytes(),
                f'Restart byte mismatch: {record["case"]}')
        check_hash(restored, record['sha256'])
        require(current_path(record['cover']).is_file(), f'Missing restart cover: {record["case"]}')
    v1 = ROOT / 'experiments/001-baseline-v1/examples'
    require((v1 / 'key-message.after-restart.txt').read_bytes() ==
            (v1 / 'key-message.txt').read_bytes(), 'V1 restart byte mismatch')
    counts['saved restart recoveries compared byte-for-byte'] = len(restarts) + 1

    # Check authored navigation; upstream research snapshots are archival sources.
    documents = [ROOT / 'README.md', ROOT / 'EXPERIMENTS.md', ROOT / 'blog/concept.md',
                 ROOT / 'poc/README.md']
    documents += sorted((ROOT / 'experiments').glob('*.md'))
    documents += sorted((ROOT / 'experiments').glob('*/*.md'))
    links = 0
    for document in documents:
        for target in re.findall(r'\[[^\]\n]+\]\(([^)\n]+)\)', document.read_text()):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            destination = document.parent / unquote(parsed.path)
            require(destination.exists(), f'Broken link in {document.relative_to(ROOT)}: {target}')
            links += 1
    counts['local documentation links'] = links

    for label, count in counts.items():
        print(f'{label}: {count}')
    for error in errors:
        print(f'FAIL: {error}', file=sys.stderr)
    if not errors:
        print('PASS: archive intact. No model inference was run.')
    return bool(errors)


if __name__ == '__main__':
    try:
        raise SystemExit(verify())
    except (OSError, ValueError, KeyError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        raise SystemExit(1)
