# The Vara Expo zone journey: one continuous road through Career, Education, Skills and Market, then a crane up
# for the summary. Shared by the still checks, the full render and the per-section exports.
import numpy as np
from road3d import build, look_at, Camera

# ---------- the road ----------
# Each zone sits on a left-hand U-turn (pin at the apex); the connector turns back right by the same 180 deg,
# so the road snakes forward and never crosses itself.
R = {'career': 8, 'education': 9, 'skills': 7.5, 'market': 8}
STEPS = [('S', 60), ('L', R['career'], 180),
         ('S', 16), ('R', 18, 80), ('S', 26), ('R', 30, 100), ('S', 34),
         ('L', R['education'], 180),
         ('S', 16), ('R', 18, 85), ('S', 22), ('R', 28, 95), ('S', 30),
         ('L', R['skills'], 180),
         ('S', 16), ('R', 18, 80), ('S', 26), ('R', 30, 100), ('S', 34),
         ('L', R['market'], 180),
         ('S', 16), ('R', 18, 80), ('S', 90)]
ROAD = build(STEPS)
ZONES = ['career', 'education', 'skills', 'market']

def _hairpins():
    """World frame (start point, heading, arclength) of each U-turn, found by replaying the steps."""
    pts, hs, s = ROAD
    out, acc = [], 0.0
    for st in STEPS:
        length = st[1] if st[0] == 'S' else np.radians(st[2])*st[1]
        if st[0] == 'L' and st[2] == 180:
            i = int(np.searchsorted(s, acc))
            out.append((pts[i], hs[i], acc))
        acc += length
    return out
HAIRPINS = dict(zip(ZONES, _hairpins()))

def local_to_world(zone, p):
    """Local hairpin frame: origin at the U-turn's start, +z along the entry heading, +x to its right, y up."""
    P0, h, _ = HAIRPINS[zone]
    x, y, z = p
    wx = P0[0] + x*np.cos(h) + z*np.sin(h); wz = P0[1] - x*np.sin(h) + z*np.cos(h)
    return np.array([wx, y, wz])

def pin(zone):
    r = R[zone]; return local_to_world(zone, (-r, 0, r))

def pin_s(zone):
    return HAIRPINS[zone][2] + np.pi*R[zone]/2

# ---------- cameras (local to each U-turn, so every zone frames its pin left with room for the title) ----------
SHOTS = {   # (camera pos, look-at target, fov) in the zone's local frame
    'career':    ((-27, 5.5, -8), (0, 3, 3), 68),          # low and dramatic, matches the reference frame
    'education': ((-25, 11, -13), (-1, 0.5, 5), 64),       # higher, looks down into the loop
    'skills':    ((-35.5, 11, 5.5), (3, 0, 0), 60),        # high side: the road S-curves away into the distance
    'market':    ((-8, 16, -8), (-1, 2, 6), 62),           # looking down: the U-turn becomes an arch
}
# Where the animator's icon and title go, relative to the pin base on the road (fractions of frame W/H):
# icon centre sits POLE above the base; the title block runs right of the icon.
POLE = .24
def title_box(base, W, H):
    ix, iy = base[0], base[1] - POLE*H
    return (int(ix - .045*W), int(iy - .08*H), int(ix + .48*W), int(iy + .075*H))

def shot(zone):
    c, t, fov = SHOTS[zone]
    return local_to_world(zone, c), local_to_world(zone, t), fov

def overview():
    """Summary: crane up over the whole road. The road sits in the lower half; the top stays clear for the title."""
    pts = ROAD[0]; c = pts.mean(0); span = np.ptp(pts, 0).max()
    target = np.array([c[0], span*.12, c[1]])
    pos = np.array([c[0], span*.68, c[1] - span*.62])
    return pos, target, 58

def camera_between(a, b, k, lift=0.0):
    """Interpolate position and look-at target separately (keeps framing sane), crane up by `lift` mid-move."""
    pa, ta, fa = a; pb, tb, fb = b
    up = np.array([0, lift*np.sin(np.pi*k), 0])
    return look_at(pa + (pb - pa)*k + up, ta + (tb - ta)*k + up*.35, fa + (fb - fa)*k)

def road_point(s_):
    pts, _, s = ROAD
    return np.array([np.interp(s_, s, pts[:, 0]), 0.0, np.interp(s_, s, pts[:, 1])])

def camera_along(za, zb, k, lift=0.0):
    """Travel along the road from zone A's pin to zone B's: the look-at point rides the road, and the camera's
    offset from it eases from shot A's to shot B's in polar form (distance, heading, height), so the road stays
    in frame for the whole move."""
    (pa, ta, fa), (pb, tb, fb) = shot(za), shot(zb)
    sa, sb = pin_s(za), pin_s(zb)
    ra, rb = road_point(sa), road_point(sb)
    target = road_point(sa + (sb - sa)*k) + (ta - ra)*(1 - k) + (tb - rb)*k
    def polar(v): return np.hypot(v[0], v[2]), np.arctan2(v[0], v[2]), v[1]
    (la, ya, ha), (lb, yb, hb) = polar(pa - ta), polar(pb - tb)
    dy = (yb - ya + np.pi) % (2*np.pi) - np.pi
    l, yw, h = la + (lb - la)*k, ya + dy*k, ha + (hb - ha)*k + lift*np.sin(np.pi*k)
    pos = target + np.array([l*np.sin(yw), h, l*np.cos(yw)])
    return look_at(pos, target, fa + (fb - fa)*k)

# ---------- road colour: each zone's palette by distance from its pin ----------
PALETTES = {
    'career':    [(0, (232, 56, 124)), (5, (240, 104, 88)), (11, (247, 166, 58)), (19, (240, 184, 40)), (30, (222, 188, 32))],
    'education': [(0, (44, 200, 74)), (7, (70, 208, 64)), (15, (130, 212, 56)), (26, (196, 208, 40))],
    'skills':    [(0, (34, 110, 230)), (6, (28, 150, 228)), (13, (30, 192, 226)), (24, (40, 206, 170))],
    'market':    [(0, (226, 64, 190)), (7, (182, 68, 236)), (15, (124, 82, 240)), (26, (62, 130, 240))],
}
def bounds():
    """Colour hand-over points: halfway (in arclength) between consecutive pins."""
    ps = [pin_s(z) for z in ZONES]
    return [(a + b)/2 for a, b in zip(ps, ps[1:])]
