#!/usr/bin/env python3
"""Run the opening-paragraph pilot and compact controls as separate processes.

Results contain only authenticated, byte-exact round trips. attempts.json keeps
the complete schedule, phase commands, and failures, including interrupted runs.
Use --dry-run to save and inspect the schedule without contacting the model.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

import compact
from compact_demo import CASES
import p2p


CODE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = CODE_ROOT.parent
EXPERIMENT = REPO_ROOT / 'experiments/003-opening-paragraph'
OPENINGS = ('conference-followup', 'stem-revision', 'history-revision',
            'project-update', 'hobby-planning')
DEFAULT_OPENINGS = OPENINGS[:3]
SEED = 20261021


def digest(data):
    return hashlib.sha256(data).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def git(*args):
    result = subprocess.run(['git', *args], cwd=REPO_ROOT, capture_output=True,
                            check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace').strip())
    return result.stdout


def source_metadata(root, args):
    paths = [CODE_ROOT / name for name in ('p2p.py', 'compact.py', 'source_codec.py',
                                         'compact_demo.py', 'opening.py', 'opening_demo.py')]
    paths += [EXPERIMENT / 'prompt-template-v1.txt']
    paths += [EXPERIMENT / 'openings' / f'{name}.txt' for name in args.openings]
    sources = {}
    for path in paths:
        relative = path.relative_to(REPO_ROOT).as_posix()
        data = path.read_bytes()
        previous = subprocess.run(['git', 'show', f'HEAD:{relative}'], cwd=REPO_ROOT,
                                  capture_output=True, check=False)
        dirty = previous.returncode != 0 or previous.stdout != data
        target = root / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        sources[relative] = {'sha256': digest(data), 'dirty': dirty,
                             'snapshot': target.relative_to(root).as_posix()}
    return {'commit': git('rev-parse', 'HEAD').decode().strip(),
            'git_status_porcelain': git('status', '--porcelain=v1', '--untracked-files=all').decode(),
            'sources': sources}


def schedule(args):
    conditions = [{'kind': 'opening', 'opening': opening, 'temperature': temperature,
                   'variant': f'opening-{opening}-t{temperature}'}
                  for opening in args.openings for temperature in args.temperatures]
    conditions += [{'kind': 'control', 'profile': profile, 'variant': f'{profile}-auto',
                    'temperature': compact.PROFILES[profile][2]}
                   for profile in args.controls]
    rng = random.Random(SEED)
    attempts = []
    # Each round contains every condition, keeping repetitions interleaved rather
    # than completing one condition before beginning the next one.
    for repetition in range(1, args.repetitions + 1):
        cases = list(args.cases)
        rng.shuffle(cases)
        for case in cases:
            order = list(conditions)
            rng.shuffle(order)
            for condition in order:
                attempts.append({'name': f'{case}.{condition["variant"]}.{repetition}',
                                 'case': case, 'repetition': repetition, **condition,
                                 'status': 'planned', 'phases': []})
    return attempts


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path,
                        default=EXPERIMENT / 'runs' / time.strftime('%Y%m%d-%H%M%S'))
    parser.add_argument('--url', default=p2p.DEFAULT_URL)
    parser.add_argument('--key', type=Path, default=CODE_ROOT / 'keys/alice.txt')
    parser.add_argument('--repetitions', type=int, default=2)
    parser.add_argument('--cases', choices=CASES, nargs='+', default=['key-message', 'paragraph'])
    parser.add_argument('--openings', choices=OPENINGS, nargs='*', default=list(DEFAULT_OPENINGS))
    parser.add_argument('--temperatures', choices=('1.0', '1.2'), nargs='+', default=['1.0', '1.2'])
    parser.add_argument('--controls', choices=('varied', 'warm'), nargs='*', default=['varied', 'warm'])
    parser.add_argument('--max-tokens', type=int, default=5000)
    parser.add_argument('--timeout-seconds', type=int, default=3600,
                        help='Maximum wall time for each encoder or decoder process.')
    parser.add_argument('--cold', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    if min(args.repetitions, args.max_tokens, args.timeout_seconds) < 1:
        parser.error('--repetitions, --max-tokens and --timeout-seconds must be positive')
    if not args.openings and not args.controls:
        parser.error('Select at least one opening or control')
    for name in ('cases', 'openings', 'temperatures', 'controls'):
        values = getattr(args, name)
        if len(values) != len(set(values)):
            parser.error(f'--{name} must not contain duplicates')
    args.directory = args.directory.resolve()
    args.key = args.key.resolve()
    return args


def command(attempt, action, args, root):
    name = attempt['name']
    script = 'opening.py' if attempt['kind'] == 'opening' else 'compact.py'
    argv = [sys.executable, str(CODE_ROOT / script), action, '--key', str(args.key),
            '--url', args.url, '--max-tokens', str(args.max_tokens), '--compression', 'auto']
    if args.cold:
        argv += ['--cold']
    if attempt['kind'] == 'opening':
        argv += ['--temperature', attempt['temperature']]
        if action == 'encode':
            argv += ['--opening', str(root / f'{name}.opening.txt')]
    else:
        argv += ['--profile', attempt['profile']]
    source = root / f'{name}.input' if action == 'encode' else root / f'{name}.cover.txt'
    target = root / f'{name}.cover.txt' if action == 'encode' else root / f'{name}.recovered'
    return argv + ['--input', str(source), '--output', str(target),
                   '--stats', str(root / f'{name}.{action}.json')]


def retain_context(root, attempt, stats):
    name = attempt['name']
    if attempt['kind'] == 'opening':
        if 'rendered_prompt' in stats:
            (root / f'{name}.prompt.txt').write_text(stats['rendered_prompt'])
        return
    prompt = compact.PROFILES[attempt['profile']][0]
    (root / f'{name}.prompt.txt').write_text(prompt)


def run_attempt(root, attempt, args, attempts):
    name = attempt['name']
    data = CASES[attempt['case']]
    (root / f'{name}.input').write_bytes(data)
    if attempt['kind'] == 'opening':
        shutil.copyfile(EXPERIMENT / 'openings' / f'{attempt["opening"]}.txt',
                        root / f'{name}.opening.txt')
        shutil.copyfile(EXPERIMENT / 'prompt-template-v1.txt',
                        root / f'{name}.prompt-template.txt')
    else:
        retain_context(root, attempt, {})
    stats = {}
    for action in ('encode', 'decode'):
        argv = command(attempt, action, args, root)
        phase = {'action': action, 'argv': argv, 'cwd': str(REPO_ROOT),
                 'started_at': utc_now(), 'status': 'running'}
        attempt['phases'].append(phase)
        save_json(root / 'attempts.json', attempts)
        started = time.monotonic()
        try:
            with (root / f'{name}.{action}.log').open('wb') as log:
                process = subprocess.run(argv, cwd=REPO_ROOT, stdout=log, stderr=log,
                                         check=False, timeout=args.timeout_seconds)
            phase['returncode'] = process.returncode
            phase['status'] = 'success' if process.returncode == 0 else 'failed'
            if process.returncode:
                raise RuntimeError(f'{action} exited {process.returncode}; see {name}.{action}.log')
            stats[action] = json.loads((root / f'{name}.{action}.json').read_text())
            retain_context(root, attempt, stats[action])
        except BaseException as error:
            phase['status'] = 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed'
            raise
        finally:
            phase['finished_at'] = utc_now()
            phase['elapsed_seconds'] = round(time.monotonic() - started, 3)
            save_json(root / 'attempts.json', attempts)
    restored = (root / f'{name}.recovered').read_bytes()
    cover_size = (root / f'{name}.cover.txt').stat().st_size
    if restored != data:
        raise RuntimeError('Exact recovered-byte comparison failed')
    if not stats['decode'].get('authenticated'):
        raise RuntimeError('Decoder did not report authenticated recovery')
    for action in ('encode', 'decode'):
        if stats[action]['cover_bytes'] != cover_size:
            raise RuntimeError(f'{action} cover_bytes omits part of the transmitted cover')
        if stats[action]['plaintext_bytes'] != len(data):
            raise RuntimeError(f'{action} plaintext_bytes differs from the original input')
    return {'name': name, 'case': attempt['case'], 'variant': attempt['variant'],
            'repetition': attempt['repetition'], 'kind': attempt['kind'],
            'opening': attempt.get('opening'), 'temperature': attempt['temperature'],
            'exact_bytes': True, 'sha256': digest(data), 'recovered_sha256': digest(restored),
            'cover_sha256': digest((root / f'{name}.cover.txt').read_bytes()), **stats}


def main(argv=None):
    args = parse_args(argv)
    root = args.directory
    # Validate required inputs before creating an otherwise misleading run folder.
    key_hash = digest(args.key.read_bytes())
    for name in args.openings:
        (EXPERIMENT / 'openings' / f'{name}.txt').read_bytes()
    attempts = schedule(args)
    root.mkdir(parents=True, exist_ok=False)
    metadata = {'started_at': utc_now(), 'argv': [sys.executable, str(Path(__file__).resolve()),
                                               *(sys.argv[1:] if argv is None else argv)],
                'cwd': str(Path.cwd()), 'dry_run': args.dry_run, 'interleaving_seed': SEED,
                'planned_attempts': len(attempts), 'url': args.url,
                'key_path': str(args.key), 'key_sha256': key_hash,
                'model': p2p.MODEL, 'model_sha256': p2p.MODEL_SHA,
                'settings': {'compression': 'auto', 'n_probs': 64,
                             'history_context_tokens': p2p.CONTEXT_TOKENS,
                             'max_tokens': args.max_tokens, 'cold': args.cold,
                             'timeout_seconds': args.timeout_seconds,
                             'cases': args.cases, 'openings': args.openings,
                             'temperatures': args.temperatures, 'controls': args.controls,
                             'repetitions': args.repetitions},
                **source_metadata(root, args)}
    save_json(root / 'metadata.json', metadata)
    save_json(root / 'attempts.json', attempts)
    save_json(root / 'results.json', [])
    if args.dry_run:
        print(f'Saved {len(attempts)} planned attempts without model inference: {root}')
        return 0
    try:
        with urllib.request.urlopen(args.url.rstrip('/') + '/props', timeout=15) as response:
            metadata['server_props'] = json.load(response)
    except (OSError, ValueError, urllib.error.URLError) as error:
        metadata['server_props_error'] = str(error)
    save_json(root / 'metadata.json', metadata)
    results = []
    try:
        for number, attempt in enumerate(attempts, 1):
            print(f'Starting {number}/{len(attempts)} {attempt["name"]}', flush=True)
            attempt.update(status='running', started_at=utc_now())
            save_json(root / 'attempts.json', attempts)
            try:
                result = run_attempt(root, attempt, args, attempts)
                results.append(result)
                save_json(root / 'results.json', results)
                attempt['status'] = 'success'
                print(json.dumps({'name': attempt['name'], 'exact_bytes': True,
                                  'plaintext_bytes': result['encode']['plaintext_bytes'],
                                  'cover_bytes': result['encode']['cover_bytes'],
                                  'encode_seconds': result['encode']['elapsed_seconds']}), flush=True)
            except Exception as error:
                attempt.update(status='failed', error=f'{type(error).__name__}: {error}')
                print(f'FAIL {attempt["name"]}: {attempt["error"]}', flush=True)
            finally:
                attempt['finished_at'] = utc_now()
                save_json(root / 'attempts.json', attempts)
    except KeyboardInterrupt:
        attempt.update(status='interrupted', error='KeyboardInterrupt')
        save_json(root / 'attempts.json', attempts)
        metadata['interrupted'] = True
        raise
    finally:
        metadata.update(finished_at=utc_now(), successful_attempts=len(results),
                        failed_attempts=sum(a['status'] == 'failed' for a in attempts))
        save_json(root / 'metadata.json', metadata)
    print(f'Completed {len(results)}/{len(attempts)} authenticated round trips: {root}', flush=True)
    return 0 if len(results) == len(attempts) else 1


if __name__ == '__main__':
    raise SystemExit(main())
