"""Export compact, reviewable evidence for a completed public-baseline series."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

from tools.verify_report import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('series_result',type=Path)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    series = json.loads(args.series_result.read_text())
    assert all(r.get('healthy') and not r.get('error') for r in series['matches']), 'Series contains invalid matches; retain their logs separately'
    root = Path(__file__).resolve().parents[1]
    hashes = series['spec']['team_source_sha256']
    assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in hashes.items()), 'Current team differs from tested version'
    evidence = {'exported_at_utc':datetime.now(timezone.utc).isoformat(),
                'series_result':str(args.series_result),'series_results':series['results'],
                'series_passed':series['passed'],
                'team_source_sha256':hashes,'matches':[]}
    for row in series['matches']:
        directory = Path(row['directory'])
        report = verify(directory)
        if series['spec'].get('require_legal_opening'):
            assert report.get('opening_legal') is True,'Opening not verified'
        clients = [json.loads(p.read_text()) for p in sorted(directory.glob('Study*-*.json'))]
        receipts = {}
        for name in ['report.json','telemetry.json','source_manifest.json']:
            receipts[name] = hashlib.sha256((directory/name).read_bytes()).hexdigest()
        evidence['matches'].append({'directory':str(directory),'report':report,'clients':clients,'evidence_sha256':receipts})
    evidence['source_verification'] = json.loads((root/'output/benchmarks/source-verification.json').read_text())
    destination = args.output or root/'docs/public-validation.json'
    destination.write_text(json.dumps(evidence,indent=2))
    print(destination)


if __name__=='__main__':
    main()
