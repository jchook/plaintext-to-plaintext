#!/usr/bin/env python3
"""Retain separate-process rejection or externally restarted replay checks.

No server is started or restarted here. Use --restart-check only after restarting
it externally. The decoder defaults to the pilot's immutable source snapshot.
--dry-run writes artifacts and planned commands without model calls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parent.parent
REJECTION_PREFIXES = {
    'model-mismatch': ('error: Cover differs from the shared model at continuation byte ',),
    'frame-length': ('error: Invalid frame length: wrong key, opening, configuration, or cover.',),
    'authentication': ('error: Frame authentication failed.',),
    'no-authenticated-message': ('error: No authenticated message recovered within the available cover and token limit.',),
    'suffix': ('error: Cover has an altered, missing, or extra sentence-completion suffix.',),
    'invalid-opening': ('error: Opening must be one nonempty printable paragraph without line breaks or controls.',
                        'error: Opening must contain ', 'error: Opening must be valid UTF-8.',
                        'error: Opening contains a reserved template delimiter or model control marker.'),
    'boundary': ('error: Cover requires an opening, exactly two separator newlines, and a continuation.',),
}
PAYLOAD_REJECTIONS = ('model-mismatch', 'frame-length', 'authentication',
                      'no-authenticated-message', 'suffix')
EXPECTED_REJECTIONS = {
    'wrong-key': PAYLOAD_REJECTIONS,
    'changed-opening': PAYLOAD_REJECTIONS,
    'changed-continuation': PAYLOAD_REJECTIONS,
    'truncated': PAYLOAD_REJECTIONS,
    'appended': ('suffix',),
    'wrong-temperature': PAYLOAD_REJECTIONS,
    'malformed-prefix': ('invalid-opening', 'boundary'),
}


def rejection_classification(case, log):
    # A process failure is evidence only when the codec itself rejects the
    # changed cover. Broken imports, runtime/server failures and timeouts do not
    # establish authentication behavior, even if no output was produced.
    lowered = log.lower()
    if case.get('timed_out') or case['returncode'] is None:
        return 'execution-failure'
    if any(marker in lowered for marker in ('traceback (most recent call last)',
            'inference http', 'cannot reach ', 'connection refused', 'connection reset',
            'timed out', 'modulenotfounderror', 'importerror', 'runtimeerror')):
        return 'infrastructure-failure'
    if case['returncode'] != 1:
        return 'unexpected-returncode'
    errors = [line for line in log.splitlines() if line.startswith('error:')]
    if not errors:
        return 'missing-codec-error'
    error = errors[-1]
    allowed = case.get('expected_error_categories', EXPECTED_REJECTIONS.get(case['case'], ()))
    for category in allowed:
        if error.startswith(REJECTION_PREFIXES[category]):
            return category
    return 'unexpected-codec-error'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def completed_opening(run):
    results = json.loads((run / 'results.json').read_text())
    choices = [row for row in results if row.get('kind') == 'opening'
               and row.get('temperature') == '1.0' and row.get('exact_bytes')]
    if not choices:
        raise ValueError('Run has no completed, exact T1.0 opening round trip.')
    row = min(choices, key=lambda value: (value['case'] != 'paragraph', value['name']))
    cover = run / (row['name'] + '.cover.txt')
    original = run / (row['name'] + '.input')
    if digest(cover.read_bytes()) != row['cover_sha256']:
        raise ValueError('Selected cover does not match its saved result hash.')
    if digest(original.read_bytes()) != row['sha256']:
        raise ValueError('Selected input does not match its saved result hash.')
    return row, cover, original


def prepare(args, root, metadata):
    run = args.run
    row, source, original = completed_opening(run)
    cover = source.read_bytes()
    opening, separator, continuation = cover.partition(b'\n\n')
    if not separator or not continuation:
        raise ValueError('Selected cover has no public-opening boundary.')
    metadata.update({'selected_attempt': row['name'], 'source_cover': str(source),
                     'source_cover_sha256': digest(cover), 'source_input': str(original),
                     'source_input_sha256': digest(original.read_bytes())})
    cases = []
    if args.restart_check:
        baseline = REPO / 'experiments/001-baseline-v1/examples/key-message.cover.txt'
        baseline_input = baseline.with_name('key-message.txt')
        variants = [('opening-after-restart', cover, 'opening.py', '1.0', source, original),
                    ('v1-after-restart', baseline.read_bytes(), 'p2p.py', None,
                     baseline, baseline_input)]
        for name, data, script, temperature, original_cover, expected in variants:
            folder = root / name
            folder.mkdir()
            copied = folder / 'cover.txt'
            copied.write_bytes(data)
            shutil.copyfile(expected, folder / 'expected.input')
            cases.append({'case': name, 'input': str(copied), 'key': str(args.key),
                          'script': script, 'temperature': temperature,
                          'source_path': str(original_cover), 'expected_rejection': False,
                          'expected_input': str(folder / 'expected.input')})
    else:
        # Appending one printable byte preserves the validity of the opening but
        # changes its authenticated bytes. Continuation mutation changes its first
        # non-whitespace byte, rather than merely changing the public separator.
        change_index = next((index for index, value in enumerate(continuation)
                             if value not in b' \t\r\n'), 0)
        changed = bytearray(continuation)
        changed[change_index] = ord('X') if changed[change_index] != ord('X') else ord('Y')
        variants = [
            ('wrong-key', cover, '1.0'),
            ('changed-opening', opening + b' Additional note.' + separator + continuation, '1.0'),
            ('changed-continuation', opening + separator + changed, '1.0'),
            ('truncated', cover[:-1], '1.0'),
            ('appended', cover + b' Extra.', '1.0'),
            ('wrong-temperature', cover, '1.2'),
            ('malformed-prefix', opening + b'\r\n\r\n' + continuation, '1.0'),
        ]
        for name, data, temperature in variants:
            folder = root / name
            folder.mkdir()
            copied = folder / 'cover.txt'
            copied.write_bytes(data)
            key = args.key
            if name == 'wrong-key':
                key = folder / 'wrong-key.bin'
                key.write_bytes(secrets.token_bytes(32))
            cases.append({'case': name, 'input': str(copied), 'key': str(key),
                          'script': 'opening.py', 'temperature': temperature,
                          'source_path': str(source), 'expected_rejection': True,
                          'expected_error_categories': list(EXPECTED_REJECTIONS[name])})
    for case in cases:
        folder = root / case['case']
        case.update({'input_sha256': digest(Path(case['input']).read_bytes()),
                     'key_sha256': digest(Path(case['key']).read_bytes()),
                     'output': str(folder / 'decoded.bin'), 'stats': str(folder / 'decode.json'),
                     'log': str(folder / 'decode.log'), 'status': 'planned'})
        case['command'] = [sys.executable, str(args.code_root / case['script']), 'decode',
                           '--url', args.url, '--key', case['key'], '--input', case['input'],
                           '--output', case['output'], '--stats', case['stats'],
                           '--max-tokens', str(args.max_tokens)]
        if case['temperature']:
            case['command'] += ['--temperature', case['temperature']]
    return cases


def execute(case, args):
    started = time.monotonic()
    case.update({'status': 'running', 'started_at': now()})
    try:
        with Path(case['log']).open('wb') as log:
            result = subprocess.run(case['command'], cwd=REPO, stdout=log, stderr=log,
                                    timeout=args.timeout_seconds, check=False)
        case['returncode'] = result.returncode
    except subprocess.TimeoutExpired:
        case.update({'returncode': None, 'error': 'Decoder subprocess timed out.', 'timed_out': True})
    except OSError as error:
        case.update({'returncode': None, 'error': str(error)})
    case.update({'elapsed_seconds': round(time.monotonic() - started, 3), 'finished_at': now(),
                 'plaintext_written': Path(case['output']).exists(),
                 'stats_written': Path(case['stats']).exists()})
    log = Path(case['log']).read_text(errors='replace')
    errors = [line for line in log.splitlines() if line.startswith('error:')]
    case['exact_error'] = errors[-1] if errors else ''
    case.setdefault('error', case['exact_error'] or (log.splitlines()[-1] if log.splitlines() else ''))
    if case['expected_rejection']:
        case['classification'] = rejection_classification(case, log)
        case['passed'] = (case['returncode'] == 1
                          and case['classification'] in case['expected_error_categories']
                          and not case['plaintext_written'] and not case['stats_written'])
    else:
        actual = Path(case['output'])
        expected = Path(case['expected_input']).read_bytes()
        case['exact_bytes'] = actual.exists() and actual.read_bytes() == expected
        try:
            stats = json.loads(Path(case['stats']).read_text())
        except (OSError, ValueError):
            stats = {}
        case['authenticated'] = stats.get('authenticated') is True
        case['passed'] = case['returncode'] == 0 and case['exact_bytes'] and case['authenticated']
        if case['passed']:
            case['error'] = ''
            case['recovered_sha256'] = digest(actual.read_bytes())
    case['status'] = 'passed' if case['passed'] else 'failed'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True, help='New evidence directory; never overwritten')
    parser.add_argument('--code-root', type=Path, help='Defaults to run/source/poc snapshot')
    parser.add_argument('--key', type=Path, help='Defaults to run metadata key path')
    parser.add_argument('--url', help='Defaults to run metadata inference URL')
    parser.add_argument('--max-tokens', type=int, default=5000)
    parser.add_argument('--timeout-seconds', type=int, default=1800)
    parser.add_argument('--restart-check', action='store_true')
    parser.add_argument('--restart-note', default='', help='Externally managed restart details, if known')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        if min(args.max_tokens, args.timeout_seconds) < 1:
            raise ValueError('Token and timeout limits must be positive.')
        args.run, args.directory = args.run.resolve(), args.directory.resolve()
        run_meta = json.loads((args.run / 'metadata.json').read_text())
        args.key = (args.key or Path(run_meta['key_path'])).resolve()
        args.url = args.url or run_meta['url']
        args.code_root = (args.code_root or args.run / 'source/poc').resolve()
        if not args.key.read_bytes():
            raise ValueError('Key file is empty.')
        source_hashes = {name: digest((args.code_root / name).read_bytes())
                         for name in ('opening.py', 'p2p.py', 'compact.py', 'source_codec.py')}
        # Validate selection before creating the output directory.
        completed_opening(args.run)
        root = args.directory
        root.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(__file__, root / 'opening_validate.py')
        metadata = {'started_at': now(), 'run': str(args.run), 'run_commit': run_meta.get('commit'),
                    'mode': 'restart-check' if args.restart_check else 'negative-checks',
                    'restart_managed_externally': args.restart_check, 'restart_note': args.restart_note,
                    'dry_run': args.dry_run, 'url': args.url, 'cwd': str(REPO),
                    'code_root': str(args.code_root), 'source_sha256': source_hashes,
                    'template_path': str(args.code_root.parent / 'experiments/003-opening-paragraph/prompt-template-v1.txt'),
                    'template_sha256': digest((args.code_root.parent / 'experiments/003-opening-paragraph/prompt-template-v1.txt').read_bytes()),
                    'helper_sha256': digest(Path(__file__).read_bytes()),
                    'argv': [sys.executable, str(Path(__file__).resolve()),
                             *(sys.argv[1:] if argv is None else argv)]}
        cases = prepare(args, root, metadata)
        save_json(root / 'metadata.json', metadata)
        save_json(root / 'results.json', cases)
        if args.dry_run:
            print(f'Prepared {len(cases)} checks without model calls: {root}')
            return 0
        for case in cases:
            print(f'Starting {case["case"]}', flush=True)
            case.update(status='running', started_at=now())
            save_json(root / 'results.json', cases)
            execute(case, args)
            save_json(root / 'results.json', cases)
            print(f'{case["case"]}: {case["status"]}', flush=True)
        metadata.update({'finished_at': now(), 'passed': all(case['passed'] for case in cases),
                         'checks': len(cases)})
        save_json(root / 'metadata.json', metadata)
        return 0 if metadata['passed'] else 1
    except (OSError, ValueError, KeyError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
