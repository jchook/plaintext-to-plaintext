#!/usr/bin/env python3
"""Export exact archived round trips for the static example playground."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / 'experiments/003-opening-paragraph/runs/pilot-20261021'
OUTPUT = ROOT / 'website/dist/examples.json'
TOPICS = {'conference-followup': 'Conference follow-up', 'history-revision': 'History chapter',
          'stem-revision': 'Research note'}


def examples():
    records = []
    for message in ('key-message', 'paragraph'):
        for topic, label in TOPICS.items():
            for temperature in ('1.0', '1.2'):
                for trial in (1, 2):
                    name = f'{message}.opening-{topic}-t{temperature}.{trial}'
                    prefix = RUN / name
                    read = lambda suffix: Path(str(prefix) + suffix).read_bytes()
                    data, cover, recovered = read('.input'), read('.cover.txt'), read('.recovered')
                    encoded, decoded = json.loads(read('.encode.json')), json.loads(read('.decode.json'))
                    if data != recovered or not decoded['authenticated']:
                        raise ValueError(f'{name}: recovery evidence differs')
                    if len(cover) != encoded['full_cover_bytes']:
                        raise ValueError(f'{name}: cover length differs')
                    paragraph = encoded['opening']
                    if not cover.startswith(paragraph.encode() + b'\n\n'):
                        raise ValueError(f'{name}: opening differs')
                    records.append({'id': name, 'message_id': message, 'topic': topic,
                        'topic_label': label, 'temperature': temperature, 'trial': trial,
                        'message': data.decode(), 'cover': cover.decode(), 'opening': paragraph,
                        'recovered': recovered.decode(), 'message_bytes': len(data),
                        'packed_bytes': encoded['packed_source_bytes'], 'frame_bytes': encoded['frame_bytes'],
                        'cover_bytes': len(cover), 'compression': encoded['compression'],
                        'seconds': round(encoded['elapsed_seconds'] + decoded['elapsed_seconds'], 1),
                        'message_sha256': hashlib.sha256(data).hexdigest(),
                        'cover_sha256': hashlib.sha256(cover).hexdigest(),
                        'artifact_path': str(prefix.relative_to(ROOT))})
    return {'format': 'plaintext-recorded-examples-v1', 'model': 'Llama 3.2 3B · Q4_K_M',
            'protocol': 'opening-v1', 'examples': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    content = json.dumps(examples(), ensure_ascii=False, indent=2) + '\n'
    if args.check:
        if OUTPUT.read_text() != content:
            raise SystemExit('Recorded examples are stale. Run python3 scripts/export_examples.py')
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(content)
    print('24 archived, authenticated round trips verified.')


if __name__ == '__main__':
    main()
