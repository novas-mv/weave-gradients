# A 3D road on a ground plane, seen through a perspective camera.
#
# The road is built from turtle steps (straights and arcs). Its colour runs along its length through the zones,
# so the far end of the road shows where the journey goes next. Rendered as depth-sorted quads, supersampled,
# with a thin glow, optionally motion-blurred by averaging sub-frames.
import numpy as np, cv2

ROAD_WIDTH = 4.0

def build(steps, start=(0.0, 0.0), heading=0.0, ds=0.25):
    """steps: ('S', length) | ('L'/'R', radius, degrees). Returns centreline (n,2) in x/z, headings, arclength."""
    p = np.array(start, float); h = heading; pts = [p.copy()]; hs = [h]
    for st in steps:
        if st[0] == 'S':
            n = max(1, int(st[1]/ds))
            for _ in range(n):
                p = p + ds*np.array([np.sin(h), np.cos(h)]); pts.append(p.copy()); hs.append(h)
        else:
            r, deg = st[1], st[2]; sgn = -1 if st[0] == 'L' else 1
            n = max(1, int(abs(np.radians(deg))*r/ds)); dh = sgn*np.radians(deg)/n
            for _ in range(n):
                h += dh/2; p = p + (abs(np.radians(deg))*r/n)*np.array([np.sin(h), np.cos(h)]); h += dh/2
                pts.append(p.copy()); hs.append(h)
    pts = np.array(pts); s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    return pts, np.array(hs), s

class Camera:
    """pos (x, y, z) with y up; yaw around y (0 looks along +z); pitch down in degrees; fov horizontal degrees."""
    def __init__(self, pos, yaw, pitch, fov=58):
        self.pos, self.yaw, self.pitch, self.fov = np.array(pos, float), yaw, pitch, fov
    def project(self, P, W, H):
        d = P - self.pos
        cy, sy = np.cos(np.radians(self.yaw)), np.sin(np.radians(self.yaw))
        x = d[..., 0]*cy - d[..., 2]*sy; z = d[..., 0]*sy + d[..., 2]*cy; y = d[..., 1]
        cp, sp = np.cos(np.radians(self.pitch)), np.sin(np.radians(self.pitch))
        y2 = y*cp + z*sp; z2 = -y*sp + z*cp
        f = (W/2)/np.tan(np.radians(self.fov/2))
        return np.stack([W/2 + f*x/np.maximum(z2, 1e-3), H/2 - f*y2/np.maximum(z2, 1e-3)], -1), z2

def look_at(pos, target, fov=60):
    d = np.array(target, float) - np.array(pos, float)
    yaw = np.degrees(np.arctan2(d[0], d[2])); pitch = np.degrees(np.arctan2(-d[1], np.hypot(d[0], d[2])))
    return Camera(pos, yaw, pitch, fov)

def lerp_cam(a, b, k, lift=0.0):
    yaw = a.yaw + ((b.yaw - a.yaw + 180) % 360 - 180)*k
    pos = a.pos + (b.pos - a.pos)*k; pos[1] += lift*np.sin(np.pi*k)
    return Camera(pos, yaw, a.pitch + (b.pitch - a.pitch)*k, a.fov + (b.fov - a.fov)*k)

def colour_at(s, stops):
    """stops: [(arclength, (r,g,b)), ...] -> (n,3)."""
    xs = [t[0] for t in stops]; cs = np.array([t[1] for t in stops], float)
    return np.stack([np.interp(s, xs, cs[:, k]) for k in range(3)], -1)

def zone_colours(road, pins, palettes, bounds, seam=.35):
    """Per-vertex colour: each zone's palette by world distance from that zone's pin, zones split at arclength
    bounds, soft blend across each bound plus a faint light seam. pins: [(x,z)], palettes: [[(metres,(r,g,b))...]]."""
    pts, _, s = road
    cols = []
    for pin, pal in zip(pins, palettes):
        d = np.linalg.norm(pts - np.array(pin), axis=1)
        cols.append(colour_at(d, pal))
    out = cols[0]
    for i, b in enumerate(bounds):
        k = np.clip((s - (b - 4))/8, 0, 1); k = k*k*(3 - 2*k)
        out = out*(1 - k[:, None]) + cols[i + 1]*k[:, None]
        g = np.exp(-((s - b)/2.2)**2)*seam
        out = out + (255 - out)*g[:, None]
    return out

def render(cam, road, stops, W, H, ss=3, near=0.5, fog=None):
    """Returns premultiplied rgb (H,W,3 float 0-255, RGB order) and alpha (H,W float 0-1).
    fog=(start, end): the road fades out between these camera distances, so far-off road never floats on the horizon."""
    pts, hs, s = road
    nrm = np.stack([np.cos(hs), -np.sin(hs)], -1)*ROAD_WIDTH/2
    L, R = pts + nrm, pts - nrm
    to3 = lambda q: np.stack([q[:, 0], np.zeros(len(q)), q[:, 1]], -1)
    pl, zl = cam.project(to3(L), W*ss, H*ss); pr, zr = cam.project(to3(R), W*ss, H*ss)
    col = stops if isinstance(stops, np.ndarray) else colour_at(s, stops)     # per-vertex colours or stops
    canvas = np.zeros((H*ss, W*ss, 3), np.float32); alpha = np.zeros((H*ss, W*ss), np.float32)
    depth = np.minimum(np.minimum(zl[:-1], zl[1:]), np.minimum(zr[:-1], zr[1:]))
    order = np.argsort(-np.maximum(np.maximum(zl[:-1], zl[1:]), np.maximum(zr[:-1], zr[1:])))   # far to near
    lim = 4*max(W, H)*ss
    for i in order:
        if depth[i] < near: continue
        quad = np.array([pl[i], pl[i+1], pr[i+1], pr[i]])
        if np.abs(quad).max() > lim: continue
        q = np.round(quad).astype(np.int32)
        f = 1.0
        if fog:
            k = np.clip((depth[i] - fog[0])/(fog[1] - fog[0]), 0, 1); f = 1 - k*k*(3 - 2*k)
            if f <= 0: continue
        c = col[i]*f
        cv2.fillConvexPoly(canvas, q, (float(c[0]), float(c[1]), float(c[2])), lineType=cv2.LINE_8)
        cv2.fillConvexPoly(alpha, q, f, lineType=cv2.LINE_8)
    rgb = cv2.resize(canvas, (W, H), interpolation=cv2.INTER_AREA)
    a = cv2.resize(alpha, (W, H), interpolation=cv2.INTER_AREA)
    return rgb, a

def composite(bg_bgr, rgb, a, glow=True):
    """Road over a background (BGR float), with a thin warm glow and a faint wide bloom like the reference."""
    out = bg_bgr.copy(); road_bgr = rgb[..., ::-1]          # premultiplied
    if glow:
        for sigma, amt in ((3, .55), (16, .25)):
            g = cv2.GaussianBlur(road_bgr, (0, 0), sigma*out.shape[1]/1280)
            out = 255 - (255 - out)*(1 - np.clip(g/255*amt, 0, 1))
    return out*(1 - a[..., None]) + road_bgr
