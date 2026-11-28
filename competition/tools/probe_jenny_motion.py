"""Trainer-only isolation of Jenny's walk/get-up without opponents or collisions."""
import argparse
import ctypes
import json
from pathlib import Path
import subprocess
import sys


def client():
    parser=argparse.ArgumentParser();parser.add_argument('--team',required=True);parser.add_argument('--number',type=int,required=True)
    parser.add_argument('--port',type=int,required=True);parser.add_argument('--summary',type=Path,required=True)
    parser.add_argument('--stop-file',type=Path,required=True);parser.add_argument('--mode',choices=['zero','forward','turn'],required=True)
    parser.add_argument('--reset-history',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'third_party/jenny'))
    import numpy as np
    import onnxruntime as ort
    original=ort.InferenceSession
    def session(path,*a,**kw):
        options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
        kw.setdefault('sess_options',options);kw.setdefault('providers',['CPUExecutionProvider'])
        return original(path,*a,**kw)
    ort.InferenceSession=session
    from mujococodebase.agent import Agent
    from mujococodebase.world.play_mode import PlayModeEnum
    agent=Agent(args.team,args.number,port=args.port,field='custom')
    walk=agent.skills_manager.skills['Walk']
    execute=walk.execute
    def walk_with_reset(reset,*a,**kw):
        if reset and args.reset_history:walk.previous_action.fill(0)
        return execute(reset,*a,**kw)
    walk.execute=walk_with_reset
    summary={'team':args.team,'number':args.number,'mode':args.mode,'reset_history':args.reset_history,
             'frames':0,'fallen_frames':0,'error':None,'skills':{},'sensors':None}
    def act():
        if args.stop_file.exists():raise EOFError('Training fixture completed')
        world=agent.world;summary['frames']+=1
        q=agent.robot._global_cheat_orientation
        summary['fallen_frames']+=int(1-2*(q[0]*q[0]+q[1]*q[1])<.5)
        if summary['sensors'] is None:summary['sensors']=list(agent.robot.motor_positions)
        if world.playmode is PlayModeEnum.BEFORE_KICK_OFF:
            agent.server.commit_beam((0,0),0);agent.skills_manager.execute('Neutral')
        elif agent.decision_maker.is_getting_up or agent.skills_manager.is_ready('GetUp'):
            agent.decision_maker.is_getting_up=not agent.skills_manager.execute('GetUp')
        else:
            velocity={'zero':[0.,0.],'forward':[.4,0.],'turn':[.25,0.]}[args.mode]
            agent.skills_manager.execute('Walk',target_2d=np.array(velocity),is_target_absolute=False,
                                         orientation=.2 if args.mode=='turn' else 0.,is_orientation_absolute=False)
        skill=agent.skills_manager.current_skill_name or 'Neutral'
        summary['skills'][skill]=summary['skills'].get(skill,0)+1
        agent.robot.commit_motor_targets_pd()
    agent.decision_maker.update_current_behavior=act
    try:agent.run()
    except Exception as error:
        if not args.stop_file.exists():summary['error']=str(error)
    finally:args.summary.write_text(json.dumps(summary,indent=2))


def trainer():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['zero','forward','turn'],required=True)
    parser.add_argument('--reset-history',action='store_true');parser.add_argument('--seconds',type=float,default=30)
    args=parser.parse_args();ctypes.CDLL(None).prctl(4,0)
    from tools import evaluate
    original=evaluate.subprocess.Popen
    def launch(command,*a,**kw):
        if 'team.agent' in command:
            command=list(command);command[command.index('team.agent')]='tools.probe_jenny_motion'
            command.append('--client')
            for option,count in [('--behavior',1),('--walk-target',2)]:
                if option in command:
                    index=command.index(option);del command[index:index+count+1]
            command+=['--mode',args.mode]
            if args.reset_history:command.append('--reset-history')
        return original(command,*a,**kw)
    evaluate.subprocess.Popen=launch
    sys.argv=[sys.argv[0],'--scenario','walk','--seconds',str(args.seconds),'--wall-limit','90']
    evaluate.main()


if __name__=='__main__':
    if '--client' in sys.argv:sys.argv.remove('--client');client()
    else:trainer()
