# Full zone sequence, 1920x1080 @ 25 fps: Career -> Education -> Skills -> Market -> Summary.
#
# One continuous 3D road; the camera holds on each zone's U-turn, then travels to the next. During each move the
# background wipe grows out of the road's new-colour section, LAG frames behind the camera, with a soft fabric
# edge and a crest lit in the incoming colour. Writes, per frame:
#   comp/     background + road (the slot-in version)
#   bg/       background with the wipes baked, no road
#   road/     road + glow with alpha, straight RGBA
#   matte_N/  the wipe matte for move N (only frames inside that wipe)
#   preview/  comp + stand-in pins and titles: REVIEW ONLY, never a deliverable layer (text and icons go in AE)
# plus pins.json (pin base position per frame), timing.json and metrics.csv (used to verify the timing).
#
#   python3 render_full.py <bg_root> <out_dir> <font.otf>
# bg_root/<scene>/NNNN.png: 250-frame loops at 960x540 with --overscan 0.3,0.06 (upscaled 2x here).
import sys, os, json, csv, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from road3d import render, zone_colours, look_at
from journey import *

BG_ROOT, OUT, FONT = sys.argv[1:4]
ONLY = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else None     # optional: test a few frames
W, H, FPS, LOOP = 1920, 1080, 25, 250
SCENE = {'career': 'career_warm', 'education': 'education_warm', 'skills': 'skills_warm', 'market': 'market_warm', 'summary': 'finale'}
SEQ = ZONES + ['summary']
HOLD, MOVE, MOVE_SUM, SUM_HOLD, LAG = 52, 24, 32, 75, 4
WIPE_DELAY, WIPE_LEN, WIPE_LEN_SUM = 5, 22, 28
ACCENT = {'career': (247, 160, 58), 'education': (52, 200, 90), 'skills': (40, 130, 235), 'market': (200, 70, 220)}
TITLE = {'career': ('Career Zone', 'Explore opportunities'), 'education': ('Education Zone', 'Learn & grow'),
         'skills': ('Skills Experience Zone', 'Practise & master'), 'market': ('Market Zone', 'Entertainment, food street & networking')}

# ---------- timeline ----------
SEGS, f = [], 0
for i, z in enumerate(ZONES):
    SEGS.append(dict(kind='hold', a=z, b=z, start=f, end=f + HOLD)); f += HOLD
    nxt = SEQ[i + 1]; mv = MOVE_SUM if nxt == 'summary' else MOVE
    SEGS.append(dict(kind='move', a=z, b=nxt, start=f, end=f + mv, n=i)); f += mv
SEGS.append(dict(kind='hold', a='summary', b='summary', start=f, end=f + SUM_HOLD)); f += SUM_HOLD
N = f
for sg in SEGS:
    if sg['kind'] == 'move':
        ln = WIPE_LEN_SUM if sg['b'] == 'summary' else WIPE_LEN
        sg['wipe'] = (sg['start'] + WIPE_DELAY, sg['start'] + WIPE_DELAY + ln)

def bezier_ease(x1, y1, x2, y2):
    def f(t):
        t = min(max(t, 0.0), 1.0); u = t
        for _ in range(12):
            bx = 3*(1-u)**2*u*x1 + 3*(1-u)*u**2*x2 + u**3
            dx = 3*(1-u)**2*x1 + 6*(1-u)*u*(x2-x1) + 3*u**2*(1-x2)
            if abs(dx) < 1e-6: break
            u = min(max(u - (bx - t)/dx, 0.0), 1.0)
        return 3*(1-u)**2*u*y1 + 3*(1-u)*u**2*y2 + u**3
    return f
IN_OUT, OUT_, IN_ = bezier_ease(.65, 0, .35, 1), bezier_ease(.22, 1, .36, 1), bezier_ease(.64, 0, .78, 0)
prog = lambda t, a, b, e: e((t - a)/(b - a))

def seg_at(t):
    for sg in SEGS:
        if sg['start'] <= t < sg['end']: return sg
    return SEGS[-1] if t >= N else SEGS[0]

SHOT = {z: shot(z) for z in ZONES}; SHOT['summary'] = overview()
def cam_at(t):
    sg = seg_at(t)
    if sg['kind'] == 'hold': p, tg, fov = SHOT[sg['a']]; return look_at(p, tg, fov), 0.0
    k = IN_OUT((t - sg['start'])/(sg['end'] - sg['start']))
    if sg['b'] == 'summary': return camera_between(SHOT[sg['a']], SHOT['summary'], k), k      # crane up and out
    return camera_along(sg['a'], sg['b'], k, lift=6.0), k                                    # ride the road
def fog_of(cam_t):
    sg = seg_at(cam_t); k = 0 if sg['kind'] == 'hold' else IN_OUT((cam_t - sg['start'])/(sg['end'] - sg['start']))
    d = lambda z: np.linalg.norm(SHOT[z][1] - SHOT[z][0])
    dist = d(sg['a']) + (d(sg['b']) - d(sg['a']))*k
    return (dist*2.2, dist*4.0)

# ---------- road ----------
pts, _, S = ROAD
COLS = zone_colours(ROAD, [pin(z)[[0, 2]] for z in ZONES], [PALETTES[z] for z in ZONES], bounds())
BOUNDS = bounds()
def road_at(t, blur):
    """Premultiplied road rgb + alpha at time t (frames), motion-blurred over a 180-degree shutter while moving."""
    offs = np.linspace(-.25, .25, 17) if blur else [0]         # 17 samples: no visible stepping at peak speed
    acc_c = np.zeros((H, W, 3), np.float32); acc_a = np.zeros((H, W), np.float32)
    for o in offs:
        cam, _ = cam_at(t + o)
        c, a = render(cam, ROAD, COLS, W, H, ss=1 if blur else 2, fog=fog_of(t + o))   # averaging does the AA
        acc_c += c; acc_a += a
    return acc_c/len(offs), acc_a/len(offs)
def new_mask(t, move_n, dest):
    """Where the road's incoming colour is on screen at time t (half resolution)."""
    cam, _ = cam_at(t)
    if dest == 'summary': m = np.full((len(S), 3), 255.0)
    else: m = np.where((S > BOUNDS[move_n])[:, None], 255.0, 0.0).repeat(3, 1)
    c, _ = render(cam, ROAD, m, W//2, H//2, ss=1, fog=fog_of(t))
    return c[..., 0]/255
def glow_of(rgb):
    """The reference's thin warm glow + faint wide bloom, as a screen layer (BGR, 0-255)."""
    g = np.zeros_like(rgb)
    for sigma, amt in ((4.5, .55), (24, .25)):
        b = cv2.GaussianBlur(rgb, (0, 0), sigma)*amt
        g = 255 - (255 - g)*(1 - np.clip(b/255, 0, 1))
    return g

# ---------- backgrounds ----------
OVER, PARALLAX = (.3, .06), .25
REST_ANCHOR = {}
def anchor(z): return pin(z) if z != 'summary' else SHOT['summary'][1]
for z in SEQ:
    p, tg, fov = SHOT[z]; REST_ANCHOR[z] = look_at(p, tg, fov).project(anchor(z)[None], W, H)[0][0]
_bgc = {}
def plate(z, f):
    key = (z, f % LOOP)
    if key not in _bgc:
        if len(_bgc) > 24: _bgc.clear()
        p = f'{BG_ROOT}/{SCENE[z]}/{f % LOOP:04d}.png'
        if ONLY and not os.path.exists(p): p = f'{BG_ROOT}/{SCENE[z]}/0000.png'      # test runs only
        im = cv2.imread(p).astype(np.float32)
        _bgc[key] = cv2.resize(im, (im.shape[1]*2, im.shape[0]*2), interpolation=cv2.INTER_CUBIC)
    return _bgc[key]
def bg(z, f, cam):
    big = plate(z, f)
    q, d = cam.project(anchor(z)[None], W, H)
    off = (q[0] - REST_ANCHOR[z])*PARALLAX if d[0] > 1 else np.array([OVER[0]*W, 0])*np.sign(q[0] - REST_ANCHOR[z])
    ox = np.clip(OVER[0]*W + off[0], 0, big.shape[1] - W); oy = np.clip(OVER[1]*H + off[1], 0, big.shape[0] - H)
    M = np.float32([[1, 0, -ox], [0, 1, -oy]])
    return cv2.warpAffine(big, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
lum = lambda im: float(cv2.cvtColor(np.clip(im, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).mean())
# hold every zone at Career's overall brightness so the wipes never pump (summary keeps its darker navy)
GAIN = {z: 1.0 for z in SEQ}
ref_l = lum(bg('career', 0, look_at(*SHOT['career'])))
for z in ZONES[1:]: GAIN[z] = float(np.clip(ref_l/lum(bg(z, 0, look_at(*SHOT[z]))), .85, 1.15))
DITHER = np.random.default_rng(7)

# ---------- stand-in pins + titles (preview only) ----------
ft = ImageFont.truetype(FONT, 64); fs = ImageFont.truetype(FONT.replace('Bold', 'Medium'), 32)
def standins(t, cam):
    im = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(im)
    for sg in SEGS:
        if sg['kind'] != 'hold' or sg['a'] == 'summary': continue
        z = sg['a']; s0, s1 = sg['start'], sg['end']
        pv = prog(t, s0 - 2, s0 + 8, OUT_) * (1 - prog(t, s1 - 10, s1 - 2, IN_))
        tv = prog(t, s0 + 3, s0 + 15, OUT_) * (1 - prog(t, s1 - 14, s1 - 4, IN_))
        if pv <= .01 and tv <= .01: continue
        q, dd = cam.project(pin(z)[None], W, H); q = q[0]
        if dd[0] < 1: continue
        top = q - [0, POLE*H]; r = 46*(.6 + .4*pv)
        if pv > .01:
            d.line([tuple(top + [0, r]), tuple(q)], fill=(255, 255, 255, int(200*pv)), width=3)
            d.ellipse([q[0]-26, q[1]-9, q[0]+26, q[1]+9], outline=(255, 255, 255, int(170*pv)), width=3)
            d.ellipse([top[0]-r, top[1]-r, top[0]+r, top[1]+r], fill=ACCENT[z] + (int(255*pv),), outline=(255, 255, 255, int(140*pv)), width=3)
        if tv > .01:
            x, y = top[0] + 76 + 34*(1 - tv), top[1] - 46
            d.text((x, y), TITLE[z][0], font=ft, fill=(255, 255, 255, int(255*tv)))
            d.text((x + 3, y + 74), TITLE[z][1], font=fs, fill=(255, 255, 255, int(230*tv)))
    sg = SEGS[-1]
    tv = prog(t, sg['start'] + 6, sg['start'] + 20, OUT_)
    if tv > .01:
        d.text((150 - 30*(1 - tv), 420), 'VARA EXPO 2026', font=ImageFont.truetype(FONT, 96), fill=(255, 255, 255, int(255*tv)))
        d.text((154 - 30*(1 - tv), 540), 'Stand-in summary title', font=fs, fill=(255, 255, 255, int(200*tv)))
    return np.asarray(im).astype(np.float32)/255

# ---------- render ----------
for d in ['comp', 'bg', 'road', 'preview'] + [f'matte_{sg["n"]}' for sg in SEGS if sg['kind'] == 'move']:
    os.makedirs(f'{OUT}/{d}', exist_ok=True)
yy, xx = np.mgrid[0:H//2, 0:W//2].astype(np.float32)
road_cache, pins, rows = {}, {z: {} for z in ZONES}, []
for f in (ONLY or range(N)):
    sg = seg_at(f); cam, ck = cam_at(f)
    # road (holds reuse one render)
    key = ('hold', sg['a']) if sg['kind'] == 'hold' else ('f', f)
    if key not in road_cache:
        if sg['kind'] != 'hold': road_cache = {k: v for k, v in road_cache.items() if k[0] == 'hold'}
        road_cache[key] = road_at(f, sg['kind'] == 'move')
    rgb, ra = road_cache[key]; road_bgr = rgb[..., ::-1].copy()
    # background, with the wipe during moves
    za, zb = sg['a'], sg['b']
    A = bg(za, f, cam)*GAIN[za]
    m = None; k = 0.0; out = A
    if sg['kind'] == 'move' and f >= sg['wipe'][0]:
        B = bg(zb, f, cam)*GAIN[zb]
        k = prog(f, *sg['wipe'], IN_OUT)
        if f >= sg['wipe'][1] - 1 and k >= .999: m = np.ones((H, W), np.float32); out = B
        else:
            warp = 26*np.sin(xx/130 + f*.08) + 18*np.sin(yy/90 - f*.06 + 1.7)          # fabric edge, half-res px
            if zb == 'summary':
                # craning up into the sky: the navy comes down from the top like dusk (a darker scene soaking out
                # of the road reads as stains)
                field = yy + 2*warp; soft = .12*W/2
            else:
                src = new_mask(f - LAG, sg['n'], zb) > .5
                dist = cv2.distanceTransform((~src).astype(np.uint8), cv2.DIST_L2, 5) if src.any() else (W//2 - xx)
                field = dist + warp; soft = .07*W/2
            R = float(np.quantile(field[::3, ::3], k))
            mh = 1 - np.clip((field - R + soft)/(2*soft), 0, 1); mh = mh*mh*(3 - 2*mh)
            m = cv2.resize(mh, (W, H), interpolation=cv2.INTER_LINEAR)
            out = A*(1 - m[..., None]) + B*m[..., None]
            band = cv2.resize(np.exp(-((field - R)/(.045*W/2))**2), (W, H))
            ca = (band*.32*(1 - k*.6))[..., None]
            lit = 255 - (255 - out)*(255 - B)/255
            out = out*(1 - ca) + lit*ca
    if sg['kind'] == 'move' and f >= sg['wipe'][1]:
        out = bg(zb, f, cam)*GAIN[zb]; m = np.ones((H, W), np.float32)
    out = out + DITHER.uniform(-1, 1, out.shape).astype(np.float32)          # breaks up banding from the 2x upscale
    bgonly = np.clip(out, 0, 255)
    # road + glow
    glow = glow_of(road_bgr)
    comp = 255 - (255 - bgonly)*(255 - glow)/255
    comp = comp*(1 - ra[..., None]) + road_bgr
    # road layer as straight RGBA (road over its own glow), for AE
    ga = np.clip(glow.max(2)/255, 0, 1); a_tot = ra + ga*(1 - ra)
    prem = road_bgr + glow*(1 - ra[..., None])
    straight = prem/np.maximum(a_tot[..., None], 1e-4)
    cv2.imwrite(f'{OUT}/road/{f:04d}.png', np.dstack([np.clip(straight, 0, 255), a_tot[..., None]*255]).astype(np.uint8))
    cv2.imwrite(f'{OUT}/bg/{f:04d}.png', bgonly.astype(np.uint8))
    cv2.imwrite(f'{OUT}/comp/{f:04d}.png', np.clip(comp, 0, 255).astype(np.uint8))
    if m is not None and sg['kind'] == 'move' and sg['wipe'][0] <= f < sg['wipe'][1]:
        cv2.imwrite(f'{OUT}/matte_{sg["n"]}/{f:04d}.png', (m*255).astype(np.uint8))
    ov = standins(f, cam); oa = ov[..., 3:4]
    sh = cv2.GaussianBlur(oa[..., 0], (0, 0), 10)[..., None]
    pv = comp*(1 - .35*np.clip(sh*1.5, 0, 1)); pv = pv*(1 - oa) + ov[..., [2, 1, 0]]*255*oa
    cv2.imwrite(f'{OUT}/preview/{f:04d}.png', np.clip(pv, 0, 255).astype(np.uint8))
    for z in ZONES:
        q, dd = cam.project(pin(z)[None], W, H)
        if dd[0] > 1 and -200 < q[0][0] < W + 200 and -200 < q[0][1] < H + 200: pins[z][f] = [round(float(q[0][0]), 2), round(float(q[0][1]), 2)]
    g = cv2.cvtColor(np.clip(comp, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    bgo = cv2.cvtColor(bgonly.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    rows.append(dict(frame=f, seg=sg['kind'] + ':' + za + '>' + zb, cam=round(ck, 4), wipe=round(k, 4),
                     coverage=round(float(m.mean()), 4) if m is not None else 0.0,
                     bg_luma=round(float(bgo[ra < .05].mean()), 2), road_luma=round(float(g[ra > .9].mean()), 2) if (ra > .9).any() else 0,
                     crest_peak=round(float(bgo[(ra < .05) & ((m if m is not None else np.zeros_like(ra)) > .3) & ((m if m is not None else np.ones_like(ra)) < .7)].max()), 2)
                       if m is not None and ((ra < .05) & (m > .3) & (m < .7)).any() else 0))
    if f % 25 == 0: print(f'{f}/{N}', flush=True)

if ONLY: sys.exit(print('test frames written', ONLY))
json.dump(pins, open(f'{OUT}/pins.json', 'w'))
json.dump(dict(fps=FPS, frames=N, segments=SEGS, gain=GAIN), open(f'{OUT}/timing.json', 'w'), indent=1, default=str)
with open(f'{OUT}/metrics.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print('done', N, 'frames; gains', {z: round(v, 3) for z, v in GAIN.items()})
