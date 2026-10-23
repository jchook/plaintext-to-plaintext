#!/usr/bin/env python3
"""Run separately declared post-hoc ordinary-generation controls after the sweep."""
from pathlib import Path
import datetime
import hashlib
import json
import random
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'poc'))
import p2p
import opening
opening.TEMPERATURES=('0.8','1.0','1.2','1.4','1.6')


def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    sweep=ROOT/'runs/pilot-20261022'
    attempts=json.loads((sweep/'attempts.json').read_text())
    assert all(a['status'] in ('success','failed','interrupted') for a in attempts), 'Wait for sweep to finish'
    root=ROOT/'controls/pilot-20261022'
    root.mkdir(parents=True,exist_ok=False)
    public=(REPO/'experiments/003-opening-paragraph/openings/conference-followup.txt').read_bytes()
    (root/'opening.txt').write_bytes(public)
    rows=[{'temperature':t,'seed':202610220+i,'status':'planned'} for i,t in enumerate(opening.TEMPERATURES)]
    random.Random(202610225).shuffle(rows)
    ids={r['temperature']:hashlib.sha256(f"ordinary-blind-202610225-{i}".encode()).hexdigest()[:12]
         for i,r in enumerate(rows)}
    save(root/'blind-mapping.json',ids)
    metadata={'started_at':now(),'argv':sys.argv,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
              'model':p2p.MODEL,'model_sha256':p2p.MODEL_SHA,'protocol':'../../controls-protocol.md',
              'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'controls-protocol.md')},
              'sampling_caveat':'Normal top64 generation; no prefix-free restrictions, payload mapping, or greedy completion suffix.'}
    save(root/'metadata.json',metadata)
    save(root/'attempts.json',rows)
    reviews=[]
    try:
        with p2p.server_lock(p2p.DEFAULT_URL):
            for number,row in enumerate(rows,1):
                name='t'+row['temperature']
                row.update(status='running',started_at=now())
                save(root/'attempts.json',rows)
                started=time.monotonic()
                try:
                    model=opening.CoverModel(opening=public,temperature=row['temperature'])
                    request={'prompt':model.base,'n_predict':512,'temperature':float(row['temperature']),
                             'top_k':64,'top_p':1.0,'min_p':0.0,'typical_p':1.0,'repeat_penalty':1.0,
                             'presence_penalty':0.0,'frequency_penalty':0.0,'dry_multiplier':0.0,
                             'xtc_probability':0.0,'seed':row['seed'],'stream':False,'cache_prompt':True,
                             'n_probs':0}
                    save(root/(name+'.request.json'),request)
                    response=model.request('/completion',request)
                    save(root/(name+'.response.json'),response)
                    continuation=response['content'].encode('utf-8')
                    cover=public+b'\n\n'+continuation
                    (root/(name+'.cover.txt')).write_bytes(cover)
                    row.update(status='success',cover_bytes=len(cover),continuation_bytes=len(continuation),
                               cover_sha256=hashlib.sha256(cover).hexdigest(),server_build=model.build,
                               tokens_predicted=response.get('tokens_predicted'),stop_type=response.get('stop_type'),
                               stopped_limit=response.get('stopped_limit'),stopped_eos=response.get('stopped_eos'),
                               elapsed_seconds=round(time.monotonic()-started,3))
                    reviews.append({'id':ids[row['temperature']],'opening':public.decode(),'continuation':continuation.decode()})
                except Exception as error:
                    row.update(status='failed',error=f'{type(error).__name__}: {error}',elapsed_seconds=round(time.monotonic()-started,3))
                finally:
                    row['finished_at']=now()
                    save(root/'attempts.json',rows)
                print(f'Ordinary control {number}/{len(rows)} {row["status"]}',flush=True)
    finally:
        metadata['finished_at']=now()
        save(root/'metadata.json',metadata)
    random.Random(202610226).shuffle(reviews)
    review=root/'blind-review'
    review.mkdir()
    save(review/'batch-01.json',{'assessment':'blinded machine assessment; secondary ordinary-generation controls',
                               'rubric':'../../../README.md#frozen-plausibility-assessment','samples':reviews})
    print(review/'batch-01.json',flush=True)
    return 0 if all(r['status']=='success' for r in rows) else 1


if __name__=='__main__':
    raise SystemExit(main())
