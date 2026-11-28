"""Render genuine recorded MuJoCo states to MP4; never re-simulate the game."""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault('MUJOCO_GL','egl')
import imageio_ffmpeg
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def draw_minimap(draw, model, qpos, width, height, font):
    scale=width/1280
    map_w,map_h=int(256*scale),int(168*scale)
    margin,pad=int(18*scale),int(12*scale)
    left,top=width-map_w-margin,height-map_h-margin
    draw.rounded_rectangle((left,top,left+map_w,top+map_h),radius=int(8*scale),fill=(12,35,30),outline=(185,210,190),width=max(1,int(scale)))
    x0,y0,x1,y1=left+pad,top+pad,left+map_w-pad,top+map_h-pad
    draw.rectangle((x0,y0,x1,y1),outline=(153,184,160),width=max(1,int(scale)))
    draw.line(((x0+x1)/2,y0,(x0+x1)/2,y1),fill=(153,184,160),width=max(1,int(scale)))
    def point(x,y):return x0+(x+27.5)/55*(x1-x0),y0+(18-y)/36*(y1-y0)
    radius=max(3,int(4*scale))
    for index,kind in enumerate(model.jnt_type):
        if kind!=mujoco.mjtJoint.mjJNT_FREE:continue
        name=model.body(int(model.jnt_bodyid[index])).name
        if not name.startswith('r-'):continue
        _,side,number,*_=name.split('-');adr=int(model.jnt_qposadr[index]);x,y=point(*qpos[adr:adr+2])
        color=(75,153,255) if side=='0' else (255,92,87)
        draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=color)
        draw.text((x+radius+1,y-radius-int(3*scale)),number,font=font,fill=(240,244,241))
    x,y=point(*qpos[:2]);radius=max(2,int(3*scale))
    draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=(255,244,156),outline=(35,35,35))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--highlights',action='store_true')
    parser.add_argument('--width',type=int,default=1280)
    parser.add_argument('--height',type=int,default=720)
    parser.add_argument('--speed',type=float,default=1.)
    parser.add_argument('--camera',choices=['auto','overview','follow','closeup'],default='auto')
    parser.add_argument('--camera-distance',type=float)
    parser.add_argument('--crf',type=int,default=16)
    parser.add_argument('--start-time',type=float,default=0.)
    parser.add_argument('--end-time',type=float,default=float('inf'))
    parser.add_argument('--no-minimap',action='store_true')
    args=parser.parse_args()
    if args.width%2 or args.height%2 or args.width<320 or args.height<180:
        parser.error('Use even dimensions of at least 320 x 180')
    if not 0<=args.crf<=51 or args.speed<=0 or args.end_time<args.start_time:
        parser.error('Invalid CRF, playback speed, or time range')
    replay=args.directory/'replay'; spec=json.loads((replay/'manifest.json').read_text())
    if args.output.exists(): raise SystemExit('Output exists; refusing to replace it')
    model=mujoco.MjModel.from_binary_path(str(replay/spec['model']))
    model.vis.global_.offwidth=max(args.width,model.vis.global_.offwidth)
    model.vis.global_.offheight=max(args.height,model.vis.global_.offheight)
    data=mujoco.MjData(model)
    renderer=mujoco.Renderer(model,height=args.height,width=args.width,max_geom=max(10000,model.ngeom*2))
    camera=mujoco.MjvCamera();mujoco.mjv_defaultCamera(camera)
    camera.azimuth=90.;camera.elevation=-62.;camera.distance=52.
    camera.lookat[:]=[0,0,0]
    scale=args.width/1280
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',round(22*scale))
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',round(16*scale))
    map_font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',max(9,round(11*scale)))
    windows=[]
    report_path=args.directory/'report.json'
    report=json.loads(report_path.read_text()) if report_path.exists() else {}
    telemetry=args.directory/'telemetry.json'
    if args.highlights:
        if not telemetry.exists(): raise SystemExit('Highlights require final telemetry')
        previous=[0,0]
        for frame in json.loads(telemetry.read_text()):
            if frame['score']!=previous:
                windows.append((max(0,frame['time']-14),frame['time']+7))
                previous=frame['score']
        if not windows: windows=[(0,25)]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    writer=imageio_ffmpeg.write_frames(str(args.output),(args.width,args.height),fps=spec['fps']*args.speed,
        codec='libx264',pix_fmt_in='rgb24',pix_fmt_out='yuv420p',quality=None,macro_block_size=1,
        output_params=['-movflags','+faststart','-preset','medium','-crf',str(args.crf)])
    writer.send(None)
    frames=0
    previous_target=None;previous_time=None
    explicit_tracking=args.camera in ('follow','closeup')
    camera_mode=args.camera if args.camera!='auto' else ('legacy-closeup' if args.highlights else 'overview')
    try:
        for chunk in spec['chunks']:
            with np.load(replay/chunk) as values:
                for i,elapsed in enumerate(values['time']):
                    if not args.start_time<=elapsed<=args.end_time:continue
                    if args.highlights and not any(a<=elapsed<=b for a,b in windows): continue
                    data.qpos[:]=values['qpos'][i]
                    # Kinematics only: replay must not advance physics or repeat collision solving.
                    mujoco.mj_kinematics(model,data);mujoco.mj_comPos(model,data);mujoco.mj_camlight(model,data)
                    if camera_mode!='overview':
                        target=values['ball'][i].copy()
                        if explicit_tracking:
                            target[2]=max(.45,min(1.2,target[2]))
                            if (previous_target is not None and elapsed-previous_time<.3
                                    and np.linalg.norm(target-previous_target)<8):
                                target=.6*previous_target+.4*target
                            previous_target=target.copy();previous_time=elapsed
                        camera.lookat[:]=target
                        camera.distance=args.camera_distance or {'follow':12.5,'closeup':7.5,'legacy-closeup':15.}[camera_mode]
                        camera.elevation={'follow':-42.,'closeup':-32.,'legacy-closeup':-48.}[camera_mode]
                    elif args.camera_distance:
                        camera.distance=args.camera_distance
                    renderer.update_scene(data,camera=camera)
                    frame=Image.fromarray(renderer.render());draw=ImageDraw.Draw(frame)
                    side=int(spec['our_side']);score=values['score'][i]
                    draw.rectangle((0,0,args.width,round(78*scale)),fill=(12,21,33))
                    draw.text((round(18*scale),round(9*scale)),f"StudyBlue {score[side]} : {score[1-side]} {spec['opponent'].upper()}    |    {elapsed:06.1f}s",font=font,fill='white')
                    color='RED' if side else 'BLUE'
                    draw.text((round(18*scale),round(44*scale)),f"Our team: {color} | {'Right' if side else 'Left'} side | {values['mode'][i]}",font=small,fill=(178,198,216))
                    if explicit_tracking and not args.no_minimap:
                        draw_minimap(draw,model,values['qpos'][i],args.width,args.height,map_font)
                    if not spec['complete']:
                        draw.text((18,args.height-32),'INCOMPLETE RUN - retained prefix only',font=small,fill=(255,175,100))
                    if frames==0:frame.save(args.output.with_suffix('.preview.png'))
                    writer.send(np.asarray(frame));frames+=1
            print(json.dumps({'chunk':chunk,'frames':frames}),flush=True)
    finally:
        writer.close();renderer.close()
    meta={'output':str(args.output),'frames':frames,'fps':spec['fps']*args.speed,'duration_seconds':frames/(spec['fps']*args.speed),
          'dimensions':[args.width,args.height],'source':str(replay),'highlights':args.highlights,'complete_match':spec['complete'],
          'camera':camera_mode,'camera_distance':float(camera.distance),'crf':args.crf,'source_fps':spec['fps'],
          'temporal_interpolation':False,'time_range':[args.start_time,args.end_time if np.isfinite(args.end_time) else None]}
    args.output.with_suffix('.metadata.json').write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta),flush=True)


if __name__=='__main__': main()
