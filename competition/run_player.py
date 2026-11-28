from team.agent import arguments, run
import json

if __name__ == '__main__':
    result = run(arguments())
    print(json.dumps({'summary': result}), flush=True)
    raise SystemExit(1 if result['error'] or not result['frames'] else 0)
