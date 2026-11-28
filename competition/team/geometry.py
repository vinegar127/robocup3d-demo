"""Metres, radians, and scalar-first (w,x,y,z) quaternions."""
import math


def rotate(vector, quaternion):
    w, x, y, z = quaternion
    vx, vy, vz = vector
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + y * tz - z * ty,
            vy + w * ty + z * tx - x * tz,
            vz + w * tz + x * ty - y * tx)


def yaw(quaternion):
    w, x, y, z = quaternion
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def rotate2(point, angle):
    c, s = math.cos(angle), math.sin(angle)
    return c * point[0] - s * point[1], s * point[0] + c * point[1]


def wrap(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def unit(vector):
    length = math.hypot(*vector)
    return (vector[0] / length, vector[1] / length) if length > 1e-6 else (1., 0.)


def camera_to_world(polar, position, quaternion, head_yaw, head_pitch):
    radius, az, el = polar
    az, el = math.radians(az), math.radians(el)
    vector = (radius * math.cos(el) * math.cos(az), radius * math.cos(el) * math.sin(az), radius * math.sin(el))
    # T1 chain: torso -> yaw joint -> pitch joint -> camera site.
    def head_rotate(v):
        x, z = math.cos(head_pitch) * v[0] + math.sin(head_pitch) * v[2], -math.sin(head_pitch) * v[0] + math.cos(head_pitch) * v[2]
        a, b = rotate2((x, v[1]), head_yaw)
        return a, b, z
    camera = head_rotate((.05, 0, .12))
    offset = (.0625 + camera[0], camera[1], .243 + .06185 + camera[2])
    relative = head_rotate(vector)
    rotated = rotate(tuple(a + b for a, b in zip(offset, relative)), quaternion)
    return tuple(a + b for a, b in zip(position, rotated))
