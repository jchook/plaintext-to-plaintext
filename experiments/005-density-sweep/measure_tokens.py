#!/usr/bin/env python3
"""Count actual visible-text tokenizer tokens after the inference sweep."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'poc'))
import p2p


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,default=Path(__file__).resolve().parent/'runs/pilot-20261022')
    parser.add_argument('--url',default=p2p.DEFAULT_URL)
    args=parser.parse_args()
    output=args.run/'tokenizer-measurements.json'
    if output.exists():
        raise SystemExit('Refusing to replace existing tokenizer measurements')
    attempts=json.loads((args.run/'attempts.json').read_text())
    assert all(a['status'] in ('success','failed','interrupted') for a in attempts), 'Run must finish first'
    rows=json.loads((args.run/'results.json').read_text())
    measurements=[]
    with p2p.server_lock(args.url):
        model=p2p.Llama(args.url)
        for row in rows:
            cover=(args.run/(row['name']+'.cover.txt')).read_bytes()
            _,continuation=cover.split(b'\n\n',1)
            counts={}
            for name,data in (('full_cover',cover),('continuation',continuation)):
                tokens=model.request('/tokenize',{'content':data.decode(),'add_special':False,'parse_special':False})['tokens']
                counts[name+'_tokenizer_tokens']=len(tokens)
            measurements.append({'name':row['name'],'cover_sha256':hashlib.sha256(cover).hexdigest(),**counts})
        document={'command':sys.argv,'measured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'model_sha256':p2p.MODEL_SHA,'server_build':model.build,
                  'request_settings':{'add_special':False,'parse_special':False},
                  'tokenize_requests':2*len(rows),'measurements':measurements}
    output.write_text(json.dumps(document,indent=2)+'\n')
    print(f'Counted full visible-text and continuation tokens for {len(rows)} covers')


if __name__=='__main__':
    main()
