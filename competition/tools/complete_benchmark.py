"""Complete an invalid benchmark case with its originally specified retry.

Only failed cases may be replaced. Valid draws or losses cannot be replaced.
All original attempts are retained alongside the corrected result.
"""
import argparse
import json
from pathlib import Path

from tools.verify_report import verify


def complete(series, replacement, invalid_attempt=None):
    result = json.loads((series/'result.json').read_text())
    report = verify(replacement)
    assert report['scenario']=='match' and report['official_half_length']
    manifest = json.loads((replacement/'source_manifest.json').read_text())
    assert all(manifest.get(k)==v for k,v in result['spec']['team_source_sha256'].items()), 'Different team source'
    matches = result['matches']
    index = next(i for i,r in enumerate(matches) if r['opponent']==report['opponent'] and int(r['swap'])==report['our_side'])
    old = matches[index]
    assert old.get('error') and not old.get('healthy'), 'Cannot replace a valid result'
    assert report['seed']==old['seed'] and report['half_seconds']==result['spec']['half_seconds'], 'Changed case specification'
    replacement_record = {**{k:old[k] for k in ['opponent','swap','seed']},'exit_code':0,
        'directory':str(replacement.resolve()),'score':report['score'],'our_goals':report['our_goals'],
        'opponent_goals':report['opponent_goals'],'won':report['won'],'healthy':True,
        'opponent_commit':report['public_commit'],'error':None,
        'retry_reason':'Original case invalid due to team registration side race', 'previous_attempt':old}
    if invalid_attempt is not None:
        replacement_record['invalid_attempt_directory'] = str(invalid_attempt.resolve())
        replacement_record['invalidation'] = json.loads((invalid_attempt/'INVALIDATED.json').read_text())
    matches[index] = replacement_record
    for opponent,summary in result['results'].items():
        rows = [r for r in matches if r['opponent']==opponent]
        healthy = all(r.get('healthy') and not r.get('error') for r in rows)
        wins = sum(r.get('our_goals',0)>r.get('opponent_goals',0) for r in rows)
        losses = sum(r.get('our_goals',0)<r.get('opponent_goals',0) for r in rows)
        gf,ga = sum(r.get('our_goals',0) for r in rows),sum(r.get('opponent_goals',0) for r in rows)
        summary.update(wins=wins,losses=losses,draws=len(rows)-wins-losses,goals_for=gf,goals_against=ga,
                       all_healthy=healthy,series_won=bool(healthy and wins>losses and gf>ga))
    result['passed'] = all(r['series_won'] for r in result['results'].values())
    destination = series/'completed_result.json'
    destination.write_text(json.dumps(result,indent=2))
    return {'output':str(destination),'passed':result['passed'],'results':result['results']}


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('series',type=Path)
    parser.add_argument('replacement',type=Path)
    parser.add_argument('--invalid-attempt',type=Path)
    args = parser.parse_args()
    print(json.dumps(complete(args.series,args.replacement,args.invalid_attempt)))
