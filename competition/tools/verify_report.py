"""Check simulation evidence rather than accepting a process exit as success."""
import argparse
import json
import math
from pathlib import Path


def verify(directory, require_win=False, require_legal_opening=False):
    report = json.loads((directory / 'report.json').read_text())
    telemetry = json.loads((directory / 'telemetry.json').read_text())
    summaries = [json.loads(p.read_text()) for p in directory.glob('Study*-*.json')]
    assert summaries and all(not s['error'] and s['frames'] >= 100 for s in summaries), 'Agent failure or insufficient frames'
    assert all(math.isfinite(v) for frame in telemetry for p in frame['players'] for v in p['pos'] + p['quat']), 'Invalid physical state'
    subject = next(s for s in summaries if s['team'] == 'StudyBlue' and s['number'] == 7) if report['scenario'] != 'match' else None
    scenario = report['scenario']
    if require_legal_opening:
        assert report.get('opening_legal') is True,'Opening placement was not verified as legal'
    if scenario == 'walk':
        target = (-3., -2.) if report.get('mirror') else (3., 2.)
        error = math.dist(subject['end_position'][:2], target)
        assert error < .35 and subject['distance_walked'] > 4 and subject['fallen_frames'] == 0, 'Walk did not reach target stably'
        report['target_error_m'] = error
    elif scenario == 'recover':
        assert subject['recovery_attempts'] >= 1 and subject['recoveries'] >= 1, 'No successful recovery'
        assert subject['fallen_frames'] > 0 and subject['end_position'][2] > .55, 'Recovery did not end standing'
    elif scenario in ('shoot', 'kick'):
        side = 1 if report.get('mirror') else 0
        assert report['score'][side] > 0 and [side, 7] in report['contacts'], 'No server-confirmed goal and contact'
        assert report.get('max_attack_progress', report['max_ball_x']) > 27.5, 'Ball did not cross opponent goal line'
        if scenario == 'kick':
            assert subject.get('kicks', 0) > 0 and report['max_ball_speed'] > 3., 'No measured leg-swing shot'
            assert subject['fallen_frames'] == 0, 'Striker lost balance'
    elif scenario == 'alignment_probe':
        assert len(summaries) == 2, 'Expected striker and standing opponent'
        assert [report['our_side'], 7] in report['contacts'], 'Striker never escaped alignment to touch the ball'
        assert report['max_attack_progress'] > 3.652, 'No one-metre forward ball progress from fixture start'
        assert subject['fallen_frames'] == 0, 'Alignment recovery lost balance'
    elif scenario == 'match':
        assert report['completed_two_halves'], 'Both halves did not finish'
        assert len(summaries) == 14, 'Expected two seven-player teams'
        public = [s for s in summaries if s.get('public_opponent')]
        ours = [s for s in summaries if s['team'] == 'StudyBlue']
        if public:
            expected_side = 'right' if report['our_side'] else 'left'
            assert all(s['side']==expected_side for s in ours), 'SIDE_ASSIGNMENT: report disagrees with actual client side'
            assert report.get('requested_our_side',report['our_side'])==report['our_side'], 'SIDE_ASSIGNMENT: requested and actual sides differ'
        assert all(s['messages_received'] > 0 for s in (ours if public else summaries)), 'A player never received a legal team message'
        assert {c[0] for c in report['contacts']} == {0, 1}, 'Both teams did not touch the ball'
        assert all(s['distance_walked'] > 1 for s in summaries if s['number'] != 1), 'Inactive field player'
        if public:
            assert len(public) == 7 and len({s['public_commit'] for s in public}) == 1, 'Unidentified public opponent'
            assert all(s['parse_errors'] == 0 and s['motor_frames'] > .85 * s['frames'] for s in public), 'Public opponent failed to act'
            assert all(s['fallen_frames'] < .85 * s['frames'] for s in public), 'Public opponent spent most of game fallen'
            report['public_commit'] = public[0]['public_commit']
            report['public_healthy'] = True
            side = report['our_side']
            report['our_goals'], report['opponent_goals'] = report['score'][side], report['score'][1-side]
            report['won'] = report['our_goals'] > report['opponent_goals']
            if require_win:
                assert report['won'], 'No score advantage against the public opponent'
        report['messages_received'] = sum(s['messages_received'] for s in summaries)
        report['recoveries'] = sum(s.get('recoveries', 0) for s in summaries)
        report['goals'] = sum(report['score'])
    elif scenario == 'pass':
        sender = next(s for s in summaries if s['number'] == 7)
        receiver = next(s for s in summaries if s['number'] == 6)
        assert sender['states'].get('PASS', 0) and sender['states'].get('PASS_RELEASE', 0), 'No deliberate pass and release'
        assert receiver['states'].get('RECEIVE_PASS', 0) and receiver['messages_received'] > 0, 'Receiver never acted on a team message'
        contacts = report.get('contact_history', [])
        numbers = [c['number'] for c in contacts if c['side'] == 0]
        assert 7 in numbers and 6 in numbers[numbers.index(7) + 1:], 'No subsequent receiver contact'
    report['validated'] = True
    (directory / 'validated.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--require-win', action='store_true')
    parser.add_argument('--require-legal-opening',action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.require_win,args.require_legal_opening)))
