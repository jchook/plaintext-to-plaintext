#!/usr/bin/env python3
"""Audit every saved round trip and write case-balanced descriptive summaries."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import statistics
import subprocess
from datetime import datetime

ROOT = Path(__file__).resolve().parent


def mean(values):
    return statistics.mean(values)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, default=ROOT/'runs/pilot-20261022')
    args = p.parse_args()
    rows = json.loads((args.run/'results.json').read_text())
    metadata = json.loads((args.run/'metadata.json').read_text())
    for relative, record in metadata['sources'].items():
        snapshot = (args.run/record['snapshot']).read_bytes()
        assert hashlib.sha256(snapshot).hexdigest()==record['sha256'], 'Source snapshot hash mismatch'
        if not record['dirty']:
            committed = subprocess.check_output(['git','show',f"{metadata['commit']}:{relative}"],cwd=ROOT.parents[1])
            assert committed==snapshot, 'Source snapshot differs from recorded commit'
    attempts = json.loads((args.run/'attempts.json').read_text())
    metrics = []
    for r in rows:
        name, e, d = r['name'], r['encode'], r['decode']
        original = (args.run/(name+'.input')).read_bytes()
        recovered = (args.run/(name+'.recovered')).read_bytes()
        cover = (args.run/(name+'.cover.txt')).read_bytes()
        opening, continuation = cover.split(b'\n\n', 1)
        assert original == recovered and r['exact_bytes'] and d['authenticated']
        assert len(cover) == e['cover_bytes'] == e['full_cover_bytes'] == d['cover_bytes']
        assert hashlib.sha256(cover).hexdigest() == r['cover_sha256']
        assert len(opening) == e['opening_bytes']
        assert e['payload_cover_bytes'] + e['suffix_bytes'] == len(continuation)
        metrics.append({'name': name, 'temperature': r['temperature'], 'case': r['case'],
                        'repetition': r['repetition'], 'original_bytes': len(original),
                        'packed_bytes': e['packed_source_bytes'], 'frame_bytes': e['frame_bytes'],
                        'full_cover_bytes': len(cover), 'opening_separator_bytes': len(opening)+2,
                        'carrying_bytes': e['payload_cover_bytes'], 'suffix_bytes': e['suffix_bytes'],
                        'full_words': len(cover.decode().split()),
                        'continuation_words': len(continuation.decode().split()),
                        'carrying_tokens': e['payload_tokens'], 'total_generated_tokens': e['total_tokens'],
                        'original_bits_per_full_cover_byte': 8*len(original)/len(cover),
                        'packed_bits_per_full_cover_byte': 8*e['packed_source_bytes']/len(cover),
                        'frame_bits_per_carrying_token': e['realized_frame_bits_per_token'],
                        'frame_bits_per_full_cover_byte': 8*e['frame_bytes']/len(cover),
                        'table_entropy_bits_per_carrying_token': e['average_table_entropy_bits'],
                        'top64_entropy_bits': e['average_top_entropy_bits'],
                        'selected_entropy_bits': e['average_selected_entropy_bits'],
                        'retained_base_probability_mass': e['average_retained_probability_mass'],
                        'encode_seconds': e['elapsed_seconds'], 'decode_seconds': d['elapsed_seconds'],
                        'cover_model_calls': e['cover_model_calls']+d['cover_model_calls'],
                        'source_encode_model_calls':e.get('source_model_calls',0),
                        'compression':e['compression'], 'authenticated_exact_bytes':True})
    for case in {m['case'] for m in metrics}:
        cell = [m for m in metrics if m['case']==case]
        assert len({(m['original_bytes'],m['packed_bytes'],m['frame_bytes'],m['compression']) for m in cell})==1, 'Source coding changed across temperature conditions'
    token_path=args.run/'tokenizer-measurements.json'
    if token_path.exists():
        token_document=json.loads(token_path.read_text())
        tokens_by_name={r['name']:r for r in token_document['measurements']}
        for m in metrics:
            row=tokens_by_name[m['name']]
            m['full_cover_tokenizer_tokens']=row['full_cover_tokenizer_tokens']
            m['continuation_tokenizer_tokens']=row['continuation_tokenizer_tokens']
            m['original_bits_per_full_cover_token']=8*m['original_bytes']/row['full_cover_tokenizer_tokens']
    groups = {}
    for temperature in sorted({m['temperature'] for m in metrics}, key=float):
        selected = [m for m in metrics if m['temperature']==temperature]
        cases = {}
        for case in sorted({m['case'] for m in selected}):
            cell=[m for m in selected if m['case']==case]
            cases[case]={'trials':len(cell), 'original_bytes':cell[0]['original_bytes'],
                         'mean_full_cover_bytes':mean([m['full_cover_bytes'] for m in cell]),
                         'range_full_cover_bytes':[min(m['full_cover_bytes'] for m in cell), max(m['full_cover_bytes'] for m in cell)],
                         'mean_original_bits_per_full_cover_byte':mean([m['original_bits_per_full_cover_byte'] for m in cell]),
                         'mean_frame_bits_per_carrying_token':mean([m['frame_bits_per_carrying_token'] for m in cell])}
        groups[temperature]={'trials':len(selected), 'cases':cases,
                             'balanced_mean_full_cover_bytes':mean([v['mean_full_cover_bytes'] for v in cases.values()]),
                             'range_full_cover_bytes':[min(m['full_cover_bytes'] for m in selected),max(m['full_cover_bytes'] for m in selected)],
                             'balanced_mean_original_bits_per_full_cover_byte':mean([v['mean_original_bits_per_full_cover_byte'] for v in cases.values()]),
                             'mean_frame_bits_per_carrying_token':mean([m['frame_bits_per_carrying_token'] for m in selected]),
                             'mean_table_entropy_bits_per_token':mean([m['table_entropy_bits_per_carrying_token'] for m in selected]),
                             'mean_encode_seconds':mean([m['encode_seconds'] for m in selected]),
                             'mean_decode_seconds':mean([m['decode_seconds'] for m in selected])}
    deltas={}
    if all(t in groups for t in ('1.2','1.6')):
        for case in groups['1.2']['cases'].keys() & groups['1.6']['cases'].keys():
            a,b=[groups[t]['cases'][case]['mean_full_cover_bytes'] for t in ('1.2','1.6')]
            deltas[case]={'t1.2_mean_bytes':a,'t1.6_mean_bytes':b,'bytes_saved':a-b,'reduction_percent':100*(a-b)/a}
        a,b=[groups[t]['balanced_mean_full_cover_bytes'] for t in ('1.2','1.6')]
        deltas['balanced_corpus']={'t1.2_mean_bytes':a,'t1.6_mean_bytes':b,'bytes_saved':a-b,'reduction_percent':100*(a-b)/a}
    summary={'source_commit':metadata['commit'], 'verified_source_snapshot_files':len(metadata['sources']), 'status_counts':dict(Counter(a['status'] for a in attempts)), 'successful_authenticated_byte_equal_trials':len(metrics),
             'definitions':{'original_rate':'original secret bits/full transmitted cover bytes; source compression included, not entropy capacity',
                            'frame_rate':'encrypted frame bits/carrying continuation tokens; framing included',
                            'balanced_size':'mean over cases of mean cover size over repetitions; each case equally weighted'},
             'cost':{'api_charge_usd':0,'local_inference':True,
                     'codec_body_seconds':sum(m['encode_seconds']+m['decode_seconds'] for m in metrics),
                     'subprocess_wall_seconds':sum(phase.get('elapsed_seconds',0) for attempt in attempts for phase in attempt['phases']),
                     'sweep_wall_seconds':(datetime.fromisoformat(metadata['finished_at'])-datetime.fromisoformat(metadata['started_at'])).total_seconds() if 'finished_at' in metadata else None,
                     'model_calls_note':'Cover encode+decode and source encode calls counted separately; source decoder calls not instrumented.',
                     'cover_model_calls':sum(m['cover_model_calls'] for m in metrics),
                     'source_encode_model_calls':sum(m['source_encode_model_calls'] for m in metrics)},
             'temperatures':groups, 't1.2_to_t1.6':deltas,'individual_metrics':metrics}
    rating_files = sorted((args.run/'blind-review').glob('ratings-root-batch-*.json'))
    if rating_files:
        mapping = json.loads((args.run/'blind-mapping.json').read_text())
        id_to_row = {mapping[m['name']]: m for m in metrics}
        graded = []
        seen = set()
        for path in rating_files:
            record = json.loads(path.read_text())
            for rating in record['ratings']:
                assert rating['id'] not in seen, 'Duplicate blind rating'
                seen.add(rating['id'])
                assert set(rating['scores']) == {'fluency','coherence_purpose','sender_recipient','unsupported_claims','repetition','ending','length'}
                assert all(isinstance(v,int) and 0<=v<=2 for v in rating['scores'].values())
                m = id_to_row[rating['id']]
                total = sum(rating['scores'].values())
                accepted = total>=11 and all(rating['scores'][k]>=1 for k in ('fluency','coherence_purpose','sender_recipient'))
                graded.append({**rating,'name':m['name'],'case':m['case'],'temperature':m['temperature'],
                               'total':total,'accepted':accepted,'rating_file':path.name})
        grouped={}
        for temperature in sorted({g['temperature'] for g in graded},key=float):
            cell=[g for g in graded if g['temperature']==temperature]
            grouped[temperature]={'rated':len(cell),'accepted':sum(g['accepted'] for g in cell),
                                   'mean_score':mean([g['total'] for g in cell]),
                                   'dimension_means':{k:mean([g['scores'][k] for g in cell]) for k in cell[0]['scores']},
                                   'failure_categories':dict(Counter(category for g in cell for category in g.get('failure_categories',[]))) }
        summary['plausibility']={'assessment':'blinded machine assessment; single reviewer, not human ratings or detection',
                                 'rated':len(graded),'temperatures':grouped,'individual_ratings':graded,
                                 'overall_failure_categories':dict(Counter(category for g in graded for category in g.get('failure_categories',[]))) }
    (args.run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'status_counts':summary['status_counts'],'temperatures':{k:{p:v[p] for p in ('trials','balanced_mean_full_cover_bytes','range_full_cover_bytes','mean_frame_bits_per_carrying_token')} for k,v in groups.items()}},indent=2))


if __name__ == '__main__':
    main()
