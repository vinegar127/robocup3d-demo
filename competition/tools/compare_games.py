"""Collect validated matches and physical diagnostics without filtering losses."""
import argparse
import json
from pathlib import Path

from tools.analyze_game import analyze
from tools.verify_report import verify


def collect(directory):
    checked = verify(directory, require_legal_opening=True)
    result = analyze(directory)
    frames = json.loads((directory/'telemetry.json').read_text())
    play = [frame for frame in frames if frame['mode'] == 'PlayOn']
    summaries = [json.loads(path.read_text()) for path in directory.glob('Study*-*.json')]
    own = [row for row in summaries if row['team'] == 'StudyBlue']
    result.update(seed=checked['seed'], half_seconds=checked['half_seconds'],
                  full_length=checked['official_half_length'],
                  healthy=checked['public_healthy'], opening_legal=checked['opening_legal'],
                  opponent_commit=checked['public_commit'],
                  configuration=checked['public_configuration'])
    result['our_states'] = {}
    for row in own:
        for state, count in row['states'].items():
            result['our_states'][state] = result['our_states'].get(state, 0) + count
    result['our_outside_field_playon_samples'] = sum(
        abs(player['pos'][1]) > 18.1 or
        (abs(player['pos'][0]) > 28.6 or (abs(player['pos'][0]) > 27.6 and abs(player['pos'][1]) > 1.83))
        for frame in play for player in frame['players'] if player['side'] == checked['our_side'])
    result['total_stationary_ball_seconds'] = 0.
    result['longest_stationary_ball_seconds'] = 0.
    anchor, start, previous = None, None, None
    for frame in frames:
        now = frame['time']
        if frame['mode'] != 'PlayOn':
            anchor, start, previous = None, None, None
            continue
        point = frame['ball'][:2]
        moved = anchor is None or sum((a-b)**2 for a,b in zip(anchor,point)) > .10**2
        if moved:
            anchor, start = point, now
        elif previous is not None:
            span = now - start
            result['longest_stationary_ball_seconds'] = max(result['longest_stationary_ball_seconds'], span)
            if span >= 2.:
                # Only intervals after the first two stationary seconds count.
                result['total_stationary_ball_seconds'] += min(now-previous, span-2.)
        previous = now
    for key in ['total_stationary_ball_seconds','longest_stationary_ball_seconds']:
        result[key] = round(result[key], 2)
    result['note'] = 'Stationary-ball spans use a 0.10 m anchor radius; no last-touch possession inference. Outside samples are diagnostic, not an inferred foul count.'
    (directory/'analysis.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directories', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    records = [collect(directory.resolve()) for directory in args.directories]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(records,indent=2),encoding='utf-8')
    for record in records:
        print(json.dumps({key:record[key] for key in ['directory','opponent','our_side','our_score',
              'our_fallen_fraction','longest_stationary_ball_seconds','max_stationary_alignment_seconds']}))


if __name__ == '__main__':
    main()
