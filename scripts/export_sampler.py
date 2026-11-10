#!/usr/bin/env python3
"""Record actual decoder candidate tables for two public experiment covers."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'poc'))
import opening
import p2p
import source_codec

RUN = ROOT / 'experiments/003-opening-paragraph/runs/pilot-20261021'
OUTPUT = ROOT / 'website/dist/sampler-recordings.json'
CASES = [('conference-followup', 'Conference follow-up'), ('history-revision', 'History chapter')]


def capture(url, key):
    records = []
    for topic, label in CASES:
        name = f'key-message.opening-{topic}-t1.2.1'
        base = RUN / name
        read = lambda suffix: Path(str(base) + suffix).read_bytes()
        metadata = json.loads(read('.decode.json'))
        material = key.read_bytes()
        assert hashlib.sha256(material).hexdigest() == metadata['key_sha256']
        cover = read('.cover.txt')
        paragraph, continuation = opening.split_cover(cover)
        encryption_key, order_key = opening.keys(material, paragraph, '1.2')
        interval, history, offset, steps = p2p.Interval(), [], 0, []
        with p2p.server_lock(url):
            oracle = opening.CoverModel(url, opening=paragraph, temperature='1.2')
            for _ in range(metadata['payload_tokens']):
                entries, ends = p2p.table(oracle.candidates(history), order_key, history)
                matches = [i for i, (item, _) in enumerate(entries) if continuation.startswith(item.raw, offset)]
                assert len(matches) == 1
                chosen = matches[0]
                rows = [{'token': item.raw.decode(), 'count': count} for item, count in entries]
                steps.append({'rows': rows, 'chosen': chosen})
                token, count = entries[chosen]
                interval.advance(0 if chosen == 0 else ends[chosen - 1], count)
                offset += len(token.raw)
                history.append(token.token_id)
            frame = interval.common_bytes(metadata['frame_bytes'])
            assert frame is not None
            packed = opening.unseal(frame, encryption_key, paragraph, '1.2')
            data = source_codec.unpack(packed, lambda: opening.SourceModel(url))
            assert data == read('.input') == read('.recovered')
            assert continuation[offset:] == p2p.finish(oracle, history, continuation[:offset])
        records.append({'id': name, 'label': label, 'opening': paragraph.decode(),
            'cover': cover.decode(), 'continuation': continuation.decode(),
            'suffix': continuation[offset:].decode(), 'ciphertext': frame.hex(),
            'message': data.decode(), 'temperature': '1.2', 'steps': steps,
            'cover_sha256': hashlib.sha256(cover).hexdigest(),
            'artifact_path': str(base.relative_to(ROOT))})
        print(f'{label}: {len(steps)} real payload tokens; authenticated recovery verified.', flush=True)
    return {'format': 'plaintext-sampler-recordings-v1', 'total': p2p.TOTAL,
            'model': p2p.MODEL, 'model_sha256': p2p.MODEL_SHA, 'records': records}


def check():
    payload = json.loads(OUTPUT.read_text())
    assert payload['format'] == 'plaintext-sampler-recordings-v1'
    for row in payload['records']:
        base = ROOT / row['artifact_path']
        assert row['cover'].encode() == Path(str(base) + '.cover.txt').read_bytes()
        assert hashlib.sha256(row['cover'].encode()).hexdigest() == row['cover_sha256']
        interval = p2p.Interval()
        emitted = []
        for step in row['steps']:
            assert sum(item['count'] for item in step['rows']) == p2p.TOTAL
            chosen = step['rows'][step['chosen']]
            start = sum(item['count'] for item in step['rows'][:step['chosen']])
            interval.advance(start, chosen['count'])
            emitted.append(chosen['token'])
        assert ''.join(emitted) + row['suffix'] == row['continuation']
        assert row['cover'] == row['opening'] + '\n\n' + row['continuation']
        frame = bytes.fromhex(row['ciphertext'])
        assert interval.common_bytes(len(frame)) == frame
    print('Both sampler recordings reconstruct the archived covers and ciphertext exactly.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--url', default=p2p.DEFAULT_URL)
    parser.add_argument('--key', type=Path, default=ROOT / 'poc/keys/alice.txt')
    args = parser.parse_args()
    if args.check:
        check()
    else:
        OUTPUT.write_text(json.dumps(capture(args.url, args.key), ensure_ascii=False, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
