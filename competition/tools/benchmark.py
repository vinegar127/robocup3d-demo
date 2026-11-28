"""Predeclared full-length, home/away public-baseline series.

Every game is retained, including losses, draws and failed opponents. No
score-based early stopping or filtering is used. A series win requires a
positive aggregate goal difference and more wins than losses per opponent.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from tools.verify_report import verify
from tools.opponents import PUBLIC_KINDS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--half', type=int, default=300)
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--seeds', type=int, nargs=2, default=[31, 32])
    parser.add_argument('--opponents',nargs='+',choices=PUBLIC_KINDS,default=['apollo','bahia'])
    parser.add_argument('--require-legal-opening',action='store_true')
    parser.add_argument('--startup-timeout',type=float,default=10.,help='Simulation seconds allowed for legal entry')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    parent = root/'output/benchmarks'
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='public-',dir=parent))
    hashes = {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((root/'team').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    cases = [{'opponent':opponent,'swap':swap,'seed':args.seeds[int(swap)]}
             for opponent in args.opponents for swap in [False,True]]
    spec = {'created':time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'half_seconds':args.half,
            'cases':cases,'team_source_sha256':hashes,'require_legal_opening':args.require_legal_opening,
            'startup_timeout':args.startup_timeout}
    (output/'spec.json').write_text(json.dumps(spec,indent=2))
    print(str(output),flush=True)
    def run(case):
        command = [sys.executable,'-m','tools.evaluate','--scenario','match','--opponent',case['opponent'],
                   '--half',str(args.half),'--seed',str(case['seed']),'--wall-limit','2400',
                   '--startup-timeout',str(args.startup_timeout)]
        if case['swap']:
            command.append('--swap-teams')
        if args.require_legal_opening:
            command.append('--require-legal-opening')
        result = subprocess.run(command,cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace')
        key = f"{case['opponent']}-{'right' if case['swap'] else 'left'}"
        (output/f'{key}.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        record = {**case,'exit_code':result.returncode}
        try:
            assert result.returncode == 0, 'Evaluation process failed; inspect the retained log'
            report = next(json.loads(line) for line in reversed(result.stdout.splitlines()) if line.startswith('{') and '"output"' in line)
            directory = Path(report['output'])
            checked = verify(directory)
            if args.require_legal_opening:
                assert checked.get('opening_legal') is True,'Opening did not pass placement checks'
            manifest = json.loads((directory/'source_manifest.json').read_text())
            assert all(manifest.get(p)==h for p,h in hashes.items()), 'Team changed while series was running'
            record.update(directory=str(directory),score=checked['score'],our_goals=checked['our_goals'],
                          opponent_goals=checked['opponent_goals'],won=checked['won'],healthy=checked['public_healthy'],
                          opponent_commit=checked['public_commit'],error=None)
            record['opening_legal']=checked.get('opening_legal')
        except Exception as error:
            record['error'] = f'{type(error).__name__}: {error}'
        (output/f'{key}.json').write_text(json.dumps(record,indent=2))
        print(json.dumps(record),flush=True)
        return record
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        records = list(pool.map(run,cases))
    summary = {}
    for opponent in args.opponents:
        matches = [r for r in records if r['opponent']==opponent]
        healthy = all(r.get('healthy') and not r.get('error') for r in matches)
        valid=[r for r in matches if r.get('healthy') and not r.get('error')]
        wins = sum(r['our_goals']>r['opponent_goals'] for r in valid)
        losses = sum(r['our_goals']<r['opponent_goals'] for r in valid)
        gf = sum(r.get('our_goals',0) for r in matches)
        ga = sum(r.get('opponent_goals',0) for r in matches)
        summary[opponent] = {'wins':wins,'draws':len(valid)-wins-losses,'losses':losses,'invalid':len(matches)-len(valid),
                             'goals_for':gf,'goals_against':ga,'all_healthy':healthy,
                             'series_won':bool(healthy and wins>losses and gf>ga)}
    final = {'spec':spec,'matches':records,'results':summary,
             'passed':args.half==300 and all(r['series_won'] for r in summary.values())}
    (output/'result.json').write_text(json.dumps(final,indent=2))
    print(json.dumps({'output':str(output),'results':summary,'passed':final['passed']}),flush=True)
    return 0 if final['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
