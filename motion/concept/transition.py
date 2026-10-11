# Concept: road-led zone transition (Career -> Education), 1280x720 @ 25 fps, 100 frames.
#
# One continuous road; the camera travels along it from the Career pin to the Education pin.
# The road's colour boundary is fixed on the road, so the camera move carries the new colour in.
# The background wipe is driven by the road: it spreads outward from the road's new-colour section,
# 4 frames behind it, with a soft fabric edge and a crest lit in the incoming colour.
#
#   python3 transition.py <bgA_dir> <bgB_dir> <font.otf> <out_dir>
# bgA_dir holds frames 0000-0062 (career_warm), bgB_dir frames 0038-0099 (education_warm), rendered at 1280x720 with
# --overscan 0.3,0.06 by motion/render.mjs --seq, so the plates can pan (parallax) without cropping the composition. Writes frames, transition.mp4 and metrics.csv (used to verify the timing).
import sys, os, csv, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

A_DIR, B_DIR, FONT, OUT = sys.argv[1:5]
W, H, FPS, N = 1280, 720, 25, 100
os.makedirs(f'{OUT}/frames', exist_ok=True)

# ---------- timeline (frames) ----------
TITLE_A_OUT = (30, 40)     # Career pin + title leave
CAM = (34, 58)             # camera travels along the road (24 f)
LAG = 4                    # background follows the road's colour by 4 frames
WIPE = (39, 61)            # background coverage 0 -> 100% (22 f); its midpoint trails the camera's by LAG
PIN_B_IN = (54, 64)        # Education pin lands as the background settles
TITLE_B_IN = (58, 70)      # Education title lands last

def bezier_ease(x1, y1, x2, y2):
    """CSS/AE-style cubic-bezier easing."""
    def f(t):
        t = min(max(t, 0.0), 1.0); u = t
        for _ in range(12):                       # solve x(u) = t by Newton
            bx = 3*(1-u)**2*u*x1 + 3*(1-u)*u**2*x2 + u**3
            dx = 3*(1-u)**2*x1 + 6*(1-u)*u*(x2-x1) + 3*u**2*(1-x2)
            if abs(dx) < 1e-6: break
            u = min(max(u - (bx - t)/dx, 0.0), 1.0)
        return 3*(1-u)**2*u*y1 + 3*(1-u)*u**2*y2 + u**3
    return f
IN_OUT = bezier_ease(.65, 0, .35, 1)      # strong ease-in-out (camera, wipe)
OUT_ = bezier_ease(.22, 1, .36, 1)        # ease-out (things arriving)
IN_ = bezier_ease(.64, 0, .78, 0)         # ease-in (things leaving)
def prog(f, span, ease): return ease((f - span[0])/(span[1] - span[0]))

# ---------- the road (world units: 1 = frame width) ----------
PTS = np.array([(-.2, .66), (.03, .47), (.17, .40), (.40, .355), (.70, .36), (.95, .33),
                (1.12, .30), (1.35, .32), (1.62, .38), (1.95, .30), (2.15, .12), (2.3, -.12)])
def catmull(P, n=60):
    P = np.vstack([P[0], P, P[-1]]); out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i-1], P[i], P[i+1], P[i+2]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(.5*((2*p1) + (-p0+p2)*t + (2*p0-5*p1+4*p2-p3)*t*t + (-p0+3*p1-3*p2+p3)*t**3))
    return np.array(out)
ROAD = catmull(PTS)
PIN_A, PIN_B = np.array([.17, .40]), np.array([1.35, .32])
CAM_A, CAM_B = np.array([0., 0.]), PIN_B - np.array([.19, .40])   # Education pin lands near where Career's sat
BOUNDARY_X = .86                                                   # colour change on the road (world x)
ROAD_W = .062
CAREER = [(0, (232, 53, 122)), (.35, (247, 168, 58)), (.8, (224, 188, 34))]
EDU = [(.86, (40, 196, 92)), (1.5, (88, 214, 74)), (2.3, (160, 222, 64))]
def ramp(stops, x):
    xs = [s[0] for s in stops]; cs = np.array([s[1] for s in stops], float)
    return np.array([np.interp(x, xs, cs[:, k]) for k in range(3)])

def cam_at(f):
    k = prog(f, CAM, IN_OUT)
    pos = CAM_A + (CAM_B - CAM_A)*k
    zoom = 1 + .05*np.sin(np.pi*k)                 # slight push mid-move for depth
    return pos, zoom, k
def to_screen(p, cam, zoom):
    c = np.array([.5, .28125])
    s = (p - cam - c)*zoom + c
    return s*W

def draw_road(f):
    """Returns road RGB (float), road alpha, and alpha of the new-colour (Education) section, in screen space."""
    cam, zoom, _ = cam_at(f)
    S = 2                                           # supersample
    rgb = np.zeros((H*S, W*S, 3), np.float32); a = np.zeros((H*S, W*S), np.float32); new = np.zeros_like(a)
    pts = to_screen(ROAD, cam, zoom)*S
    th = int(ROAD_W*W*zoom*S)
    for i in range(len(pts) - 1):
        x = ROAD[i, 0]
        col = ramp(CAREER, x) if x < BOUNDARY_X else ramp(EDU, x)
        seam = np.exp(-((x - BOUNDARY_X)/.018)**2)                  # bright seam riding the colour boundary
        col = col + (np.array([255, 250, 225]) - col)*seam*.7
        p0, p1 = tuple(int(v) for v in pts[i]), tuple(int(v) for v in pts[i+1])
        cv2.line(rgb, p0, p1, tuple(float(c) for c in col[::-1]), th, cv2.LINE_AA)   # BGR
        cv2.line(a, p0, p1, 1.0, th, cv2.LINE_AA)
        if x >= BOUNDARY_X: cv2.line(new, p0, p1, 1.0, th, cv2.LINE_AA)
    d = lambda im: cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA)
    return d(rgb), d(a), d(new)

# ---------- pins + titles (world-anchored, animated) ----------
font_t = ImageFont.truetype(FONT, 44); font_s = ImageFont.truetype(FONT.replace('Bold', 'Medium'), 24)
def overlay(f):
    im = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(im)
    cam, zoom, _ = cam_at(f)
    for pin, col, title, sub, kind in [(PIN_A, (247, 160, 58), 'Career Zone', 'Explore opportunities', 'A'),
                                       (PIN_B, (52, 200, 90), 'Education Zone', 'Learn & grow', 'B')]:
        if kind == 'A':
            pv = 1 - prog(f, (TITLE_A_OUT[0], TITLE_A_OUT[0] + 8), IN_)       # pin goes first
            tv = 1 - prog(f, (TITLE_A_OUT[0] + 2, TITLE_A_OUT[1]), IN_); tdx = -24*(1 - tv)
        else:
            pv = prog(f, PIN_B_IN, OUT_)
            tv = prog(f, TITLE_B_IN, OUT_); tdx = 28*(1 - tv)
        base = to_screen(pin, cam, zoom); top = base - np.array([0, .13*W])
        if pv > .01:
            r = 34*(.6 + .4*pv)
            d.line([tuple(top + [0, r]), tuple(base)], fill=(255, 255, 255, int(200*pv)), width=2)
            d.ellipse([base[0]-16, base[1]-6, base[0]+16, base[1]+6], outline=(255, 255, 255, int(170*pv)), width=2)
            d.ellipse([top[0]-r, top[1]-r, top[0]+r, top[1]+r], fill=col + (int(255*pv),), outline=(255, 255, 255, int(120*pv)), width=2)
        if tv > .01:
            x, y = top[0] + 52 + tdx, top[1] - 34
            d.text((x, y), title, font=font_t, fill=(255, 255, 255, int(255*tv)))
            d.text((x + 2, y + 54), sub, font=font_s, fill=(255, 255, 255, int(225*tv)))
    return np.asarray(im).astype(np.float32)/255

# ---------- backgrounds with parallax ----------
OVER, PARALLAX = (.3, .06), .25                 # plate overscan per side; background moves at 25% of the road
def bg(dirpath, f, cam, rest):
    big = cv2.imread(f'{dirpath}/{f:04d}.png').astype(np.float32)
    ox = OVER[0]*W + (cam[0] - rest[0])*W*PARALLAX; oy = OVER[1]*H + (cam[1] - rest[1])*W*PARALLAX
    ox = min(max(ox, 0), big.shape[1] - W); oy = min(max(oy, 0), big.shape[0] - H)
    M = np.float32([[1, 0, -ox], [0, 1, -oy]])
    return cv2.warpAffine(big, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

# Match B's overall brightness to A so the wipe never pumps (measured on the first rest frames).
lum = lambda im: float(cv2.cvtColor(im.astype(np.uint8), cv2.COLOR_BGR2GRAY).mean())
GAIN_B = lum(bg(A_DIR, 0, CAM_A, CAM_A)) / lum(bg(B_DIR, 99, CAM_B, CAM_B))

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
rows = []
road_cache = {}
def road(f):
    if f not in road_cache: road_cache[f] = draw_road(f)
    return road_cache[f]

for f in range(N):
    cam, zoom, ck = cam_at(f)
    rgb, ra, new_now = road(f)
    # background matte grows outward from where the road's new colour was LAG frames ago
    _, _, new_lag = road(max(f - LAG, 0))
    k = prog(f, WIPE, IN_OUT)
    if f < WIPE[0]: m = np.zeros((H, W), np.float32); R = 0
    elif f >= WIPE[1]: m = np.ones((H, W), np.float32); R = 9e9
    else:
        src = (new_lag > .5).astype(np.uint8)
        dist = cv2.distanceTransform(1 - src, cv2.DIST_L2, 5) if src.any() else np.full((H, W), 2*W, np.float32)
        warp = 26*np.sin(xx/170 + f*.08) + 18*np.sin(yy/120 - f*.06 + 1.7)           # fabric edge, not a ruler line
        field = dist + warp; soft = .07*W
        R = float(np.quantile(field[::4, ::4], k))            # coverage follows the ease exactly
        m = 1 - np.clip((field - R + soft)/(2*soft), 0, 1); m = m*m*(3 - 2*m)
    A = bg(A_DIR, f, cam, CAM_A) if f <= 62 else None
    B = bg(B_DIR, f, cam, CAM_B)*GAIN_B if f >= 38 else None
    if A is None: out = B.copy()
    elif B is None or m.max() == 0: out = A.copy()
    else: out = A*(1 - m[..., None]) + B*m[..., None]
    crest = 0.0
    if B is not None and 0 < k < 1 and R < 9e9 and A is not None:
        band = np.exp(-((dist + warp - R)/(.045*W))**2)
        crest_a = (band*.32*(1 - k*.6))[..., None]                                    # crest fades as it settles
        lit = 255 - (255 - out)*(255 - B)/255                                          # screen: light in the incoming colour
        out = out*(1 - crest_a) + lit*crest_a
        crest = float((band > .5).mean())
    # road: glow, then body
    glow = cv2.GaussianBlur(rgb*ra[..., None], (0, 0), 18)
    out = 255 - (255 - out)*(1 - np.clip(glow/255*.5, 0, 1))
    out = out*(1 - ra[..., None]) + rgb*ra[..., None]
    # pins + titles with a soft shadow
    ov = overlay(f); oa = ov[..., 3:4]
    sh = cv2.GaussianBlur(oa[..., 0], (0, 0), 8)[..., None]
    out = out*(1 - .35*np.clip(sh*1.5, 0, 1))
    out = out*(1 - oa) + ov[..., [2, 1, 0]]*255*oa
    out = np.clip(out, 0, 255).astype(np.uint8)
    cv2.imwrite(f'{OUT}/frames/{f:04d}.png', out)
    # metrics for verification
    seam_x = to_screen(np.array([BOUNDARY_X, np.interp(BOUNDARY_X, ROAD[:, 0], ROAD[:, 1])]), cam, zoom)[0]/W
    bgonly = (ra < .05) & (ov[..., 3] < .05)
    g = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY).astype(np.float32)
    road_l = float(g[ra > .9].mean()) if (ra > .9).any() else 0
    rows.append(dict(frame=f, cam=round(ck, 4), wipe=round(k, 4), coverage=round(float(m.mean()), 4),
                     seam_x=round(seam_x, 4), new_road_px=int((new_now > .5).sum()),
                     bg_luma=round(float(g[bgonly].mean()), 2), road_luma=round(road_l, 2),
                     crest_peak_luma=round(float(g[(m > .3) & (m < .7) & bgonly].max()) if ((m > .3) & (m < .7) & bgonly).any() else 0, 2),
                     matte_cx=round(float((xx*(m > .5)).sum()/max((m > .5).sum(), 1))/W, 3),
                     title_a=round(1 - prog(f, (TITLE_A_OUT[0] + 2, TITLE_A_OUT[1]), IN_), 3), title_b=round(prog(f, TITLE_B_IN, OUT_), 3)))
with open(f'{OUT}/metrics.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
os.system(f'ffmpeg -v error -y -framerate {FPS} -i {OUT}/frames/%04d.png -c:v libx264 -crf 14 -preset slow -pix_fmt yuv420p '
          f'-colorspace bt709 -color_primaries bt709 -color_trc bt709 {OUT}/transition.mp4')
print('gain_b', round(GAIN_B, 3))
