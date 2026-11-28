"""Inspect opening placement without moving players or changing the referee."""
import math


def inspect_opening(players, half_length=27.5, half_width=18., goalie_depth=4., goalie_half_width=3.65,
                    center_radius=5.5, kickoff_side=0):
    issues = []
    goalie_area = {0:[],1:[]}
    crossed_kickers=[]
    for p in players:
        side, n = p['side'],p['number']
        x,y,z = p['pos']
        identity = {'side':side,'number':n,'position':list(p['pos'])}
        in_goal = abs(x)<=half_length+1. and abs(y)<=1.83
        if abs(y)>half_width+.1 or (abs(x)>half_length+.1 and not in_goal):
            issues.append({'kind':'outside_field',**identity})
        if z<.5:
            issues.append({'kind':'not_standing',**identity})
        own_x = x if side==0 else -x
        if -half_length<=own_x<=-half_length+goalie_depth and abs(y)<=goalie_half_width:
            goalie_area[side].append(n)
        if side!=kickoff_side and (own_x>0 or math.hypot(x,y)<center_radius):
            issues.append({'kind':'opponent_kickoff_clearance',**identity})
        if side==kickoff_side and own_x>0 and math.hypot(x,y)>center_radius:
            issues.append({'kind':'wrong_half',**identity})
        elif side==kickoff_side and own_x>0:
            crossed_kickers.append((math.hypot(x,y),identity))
    if len(crossed_kickers)>1:
        for _,identity in sorted(crossed_kickers,key=lambda x:x[0])[1:]:
            issues.append({'kind':'multiple_cross_half_kickers',**identity})
    for side,numbers in goalie_area.items():
        if len(numbers)>2:
            issues.append({'kind':'too_many_in_own_goalie_area','side':side,'numbers':numbers,'allowed':2})
    return {'legal':not issues,'issues':issues,'players':players,'kickoff_side':kickoff_side,
            'note':'Read-only check against current 0.2.1 field and placement rules; no player repositioning'}
