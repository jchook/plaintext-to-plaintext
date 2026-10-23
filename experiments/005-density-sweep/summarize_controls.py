#!/usr/bin/env python3
"""Summarize the separate post-hoc controls; never mix them with payload trials."""
from collections import Counter
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parent/'controls/pilot-20261022'


def main():
    attempts=json.loads((ROOT/'attempts.json').read_text())
    mapping=json.loads((ROOT/'blind-mapping.json').read_text())
    graded={}
    for p in sorted((ROOT/'blind-review').glob('ratings-root-batch-*.json')):
        for rating in json.loads(p.read_text())['ratings']:
            assert rating['id'] not in graded
            graded[rating['id']]=rating
    rows=[]
    for a in sorted(attempts,key=lambda r:float(r['temperature'])):
        row=dict(a)
        if a['status']=='success':
            prefix='t'+a['temperature']
            cover=(ROOT/(prefix+'.cover.txt')).read_bytes()
            assert hashlib.sha256(cover).hexdigest()==a['cover_sha256']
            response=json.loads((ROOT/(prefix+'.response.json')).read_text())
            row['response_stop_fields']={k:v for k,v in response.items() if 'stop' in k or 'truncat' in k or k in ('tokens_predicted','tokens_evaluated')}
            row['full_words']=len(cover.decode().split())
            row['timings']=response.get('timings')
            rating=graded.get(mapping[a['temperature']])
            if rating:
                assert set(rating['scores'])=={'fluency','coherence_purpose','sender_recipient','unsupported_claims','repetition','ending','length'}
                assert all(isinstance(v,int) and 0<=v<=2 for v in rating['scores'].values())
                row['rating']=rating
                row['score']=sum(rating['scores'].values())
                row['accepted']=row['score']>=11 and all(rating['scores'][k]>=1 for k in ('fluency','coherence_purpose','sender_recipient'))
        rows.append(row)
    summary={'post_hoc_diagnostic':True,'contains_payload':False,'status_counts':dict(Counter(a['status'] for a in attempts)),
             'rated':len(graded),'accepted':sum(r.get('accepted',False) for r in rows),
             'failure_categories':dict(Counter(c for r in rows for c in r.get('rating',{}).get('failure_categories',[]))),
             'wall_phase_seconds':sum(a.get('elapsed_seconds',0) for a in attempts),'controls':rows}
    (ROOT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'status_counts':summary['status_counts'],'rated':summary['rated'],'accepted':summary['accepted']},indent=2))


if __name__=='__main__':
    main()
