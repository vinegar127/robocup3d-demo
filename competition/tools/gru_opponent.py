"""Run pinned RCSS-Booster-Client with CPU limits and Windows TCP framing.

No changes to perceptions, neural weights, observations, actions or strategy.
The original repository is retained intact in third_party/retricato.
"""
import argparse
from pathlib import Path
import sys
import os
from tools.opponents import GRU_KINDS

import torch

torch.set_num_threads(1)
torch.set_num_interop_threads(1)
root=Path(__file__).resolve().parents[1]
source_name=sys.argv[sys.argv.index('--source')+1] if '--source' in sys.argv else 'retricato'
if source_name not in GRU_KINDS:
    raise ValueError('Unknown pinned GRU source')
sys.path.insert(0,str(root/'third_party'/source_name))
from nn_client import Client


def receive(self):
    def exact(count):
        value=bytearray()
        while len(value)<count:
            part=self._sock.recv(count-len(value))
            if not part:
                raise ConnectionResetError('Connection closed')
            value.extend(part)
        return value
    size=int.from_bytes(exact(4),'big')
    if size>1_048_576:
        raise ValueError('Oversized frame')
    return exact(size)


def send(self,message):
    self._sock.sendall(len(message).to_bytes(4,'big')+message)


Client._receive_message=receive
Client._send_message=send
parser=argparse.ArgumentParser()
parser.add_argument('--source',choices=GRU_KINDS,default='retricato')
parser.add_argument('--team',required=True)
parser.add_argument('--number',type=int,required=True)
parser.add_argument('--port',type=int,required=True)
parser.add_argument('--work-dir',type=Path,required=True)
args=parser.parse_args()
args.work_dir.mkdir(parents=True,exist_ok=True)
os.chdir(args.work_dir)
client=Client('127.0.0.1',args.port,args.team,args.number,'T1',default_role='attacker')
client._policy_checkpoint=str(root/'third_party'/args.source/'locomotion_nn.pth')
client._policy_meta=str(root/'third_party'/args.source/'locomotion_nn_meta.json')
client.run()
