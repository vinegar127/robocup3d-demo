"""Summarize physical match evidence without mistaking last touch for possession."""
import argparse
import json
from pathlib import Path


def analyze(directory):
    report = json.loads((directory/'report.json').read_text())
    frames = json.loads((directory/'telemetry.json').read_text())
    summaries = [json.loads(p.read_text()) for p in directory.glob('Study*-*.json')]
    side = report['our_side']
    sign = -1 if side else 1
    goals, previous = [], (0,0)
    for frame in frames:
        if tuple(frame['score']) != previous:
            goals.append({'elapsed':frame['time'],'score':frame['score']})
            previous = tuple(frame['score'])
    ours = [s for s in summaries if s['team']=='StudyBlue']
    opponents = [s for s in summaries if s['team']=='StudyOrange']
    progress = [sign*f['ball'][0] for f in frames if f['mode']=='PlayOn']
    align_wait = {}
    for number in range(1,8):
        rows = []
        for line in (directory/f'StudyBlue-{number}.log').read_text(encoding='utf-8',errors='replace').splitlines():
            try:
                row = json.loads(line)
                if row.get('state','').startswith('ALIGN_'):
                    rows.append(row)
            except (ValueError,TypeError):
                pass
        waits, start, previous = [], None, None
        for row in rows:
            connected = previous is not None and row['t']-previous['t'] < 1.1
            stationary = connected and sum((a-b)**2 for a,b in zip(row['position'][:2],previous['position'][:2])) < .03**2
            if stationary:
                if start is None:
                    start = previous['t']
            elif start is not None:
                waits.append(previous['t']-start)
                start = None
            previous = row
        if start is not None:
            waits.append(previous['t']-start)
        align_wait[number] = round(max(waits,default=0),2)
    return {'directory':str(directory),'opponent':report['opponent'],'our_side':side,
            'our_score':[report['score'][side],report['score'][1-side]],'goals':goals,
            'mean_ball_progress_m':sum(progress)/max(1,len(progress)),
            'attacking_half_fraction':sum(x>0 for x in progress)/max(1,len(progress)),
            'our_kicks':sum(s.get('kicks',0) for s in ours),
            'our_recoveries':sum(s.get('recoveries',0) for s in ours),
            'our_fallen_fraction':sum(s['fallen_frames'] for s in ours)/sum(s['frames'] for s in ours),
            'opponent_fallen_fraction':sum(s['fallen_frames'] for s in opponents)/sum(s['frames'] for s in opponents),
            'max_stationary_alignment_seconds':align_wait}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    args = parser.parse_args()
    result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
