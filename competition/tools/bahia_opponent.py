"""Run the pristine BahiaRT snapshot with CPU-thread limits and lifecycle only."""
import argparse
from pathlib import Path
import sys
from tools.opponents import PYTHON_FIELDS

root = Path(__file__).resolve().parents[1]
source_name = sys.argv[sys.argv.index('--source')+1] if '--source' in sys.argv else 'bahia'
if source_name not in PYTHON_FIELDS:
    raise ValueError('Unknown pinned Python opponent')
sys.path.insert(0, str(root / 'third_party'/source_name))
import onnxruntime as ort

# Same CPU budget per policy as our client and Apollo. Inference and weights
# are unchanged; this avoids seven default thread pools oversubscribing the PC.
original_session = ort.InferenceSession


def cpu_session(path, *args, **kwargs):
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    kwargs.setdefault('sess_options', options)
    kwargs.setdefault('providers', ['CPUExecutionProvider'])
    return original_session(path, *args, **kwargs)


ort.InferenceSession = cpu_session
from mujococodebase.agent import Agent

parser = argparse.ArgumentParser()
parser.add_argument('--source',choices=PYTHON_FIELDS,default='bahia')
parser.add_argument('--team', required=True)
parser.add_argument('--number', type=int, required=True)
parser.add_argument('--host', default='127.0.0.1')
parser.add_argument('--port', type=int, required=True)
args = parser.parse_args()
Agent(args.team, args.number, args.host, args.port, field=PYTHON_FIELDS[args.source]).run()
