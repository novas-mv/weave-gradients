# Background-only handover: the five zone backgrounds drifting, joined by soft fabric wipes. No road, no camera.
#   python3 bg_package.py <bg_root> <work_dir> <deliver_dir>
# bg_root/<scene>/NNNN.png: 250-frame loops at 960x540 with --overscan 0.3,0.06 (centre-cropped, upscaled 2x here).
import sys, os, json, subprocess, numpy as np, cv2

BG_ROOT, WORK, D = sys.argv[1:4]
SKIP_LOOPS = '--skip-loops' in sys.argv
W, H, FPS, LOOP = 1920, 1080, 25, 250
SEQ = ['career', 'education', 'skills', 'market', 'summary']
SCENE = {'career': 'career_warm', 'education': 'education_warm', 'skills': 'skills_warm', 'market': 'market_warm', 'summary': 'finale'}
NUM = {z: f'{i + 1:02d}' for i, z in enumerate(SEQ)}
HOLD, MOVE, MOVE_SUM, SUM_HOLD = 52, 24, 32, 75
WIPE_DELAY, WIPE_DELAY_SUM = 2, 3          # each wipe must finish inside its window, or its last frame jumps to 100%
WIPE_LEN, WIPE_LEN_SUM = 22, 28

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
IN_OUT = bezier_ease(.65, 0, .35, 1)

# timeline: same beats as the road version (hold, then a transition window with the wipe inside it)
segs, f = [], 0
for i, z in enumerate(SEQ[:-1]):
    segs.append(dict(kind='hold', a=z, b=z, start=f, end=f + HOLD)); f += HOLD
    mv = MOVE_SUM if SEQ[i + 1] == 'summary' else MOVE
    ln = WIPE_LEN_SUM if SEQ[i + 1] == 'summary' else WIPE_LEN
    dl = WIPE_DELAY_SUM if SEQ[i + 1] == 'summary' else WIPE_DELAY
    assert dl + ln <= mv, 'wipe overruns its window'
    segs.append(dict(kind='wipe', a=z, b=SEQ[i + 1], start=f, end=f + mv, wipe=(f + dl, f + dl + ln), n=i)); f += mv
segs.append(dict(kind='hold', a='summary', b='summary', start=f, end=f + SUM_HOLD)); f += SUM_HOLD
N = f

_cache = {}
def plate(z, i):
    key = (z, i % LOOP)
    if key not in _cache:
        if len(_cache) > 12: _cache.clear()
        im = cv2.imread(f'{BG_ROOT}/{SCENE[z]}/{i % LOOP:04d}.png').astype(np.float32)
        big = cv2.resize(im, (im.shape[1]*2, im.shape[0]*2), interpolation=cv2.INTER_CUBIC)
        ox, oy = (big.shape[1] - W)//2, (big.shape[0] - H)//2
        _cache[key] = big[oy:oy + H, ox:ox + W]
    return _cache[key]
lum = lambda im: float(cv2.cvtColor(np.clip(im, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).mean())
GAIN = {z: 1.0 for z in SEQ}
for z in ['education', 'skills', 'market']:                     # hold zones at Career's brightness: wipes never pump
    GAIN[z] = float(np.clip(lum(plate('career', 0))/lum(plate(z, 0)), .85, 1.15))
rng = np.random.default_rng(3)
dither = lambda im: np.clip(im + rng.uniform(-1, 1, im.shape), 0, 255).astype(np.uint8)
def ff(args): subprocess.run(['ffmpeg', '-v', 'error', '-y', *args], check=True)
BT709 = ['-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv']
PRORES = lambda profile: ['-vf', 'scale=out_color_matrix=bt709:out_range=tv', '-c:v', 'prores_ks', '-profile:v', str(profile), '-pix_fmt', 'yuv422p10le', '-vendor', 'apl0', *BT709]

for sub in ['01-zone-background-loops', '02-full-sequence-with-wipes/wipe-mattes']: os.makedirs(f'{D}/{sub}', exist_ok=True)

# ---------- full sequence ----------
hx, hy = np.mgrid[0:H//2, 0:W//2][::-1].astype(np.float32)        # half-res x, y
os.makedirs(f'{WORK}/seq', exist_ok=True)
for s in segs:
    if s['kind'] == 'wipe': os.makedirs(f'{WORK}/matte_{s["n"]}', exist_ok=True)
for fr in range(N):
    s = next(x for x in segs if x['start'] <= fr < x['end'])
    A = plate(s['a'], fr)*GAIN[s['a']]; out = A; m = None
    if s['kind'] == 'wipe':
        w0, w1 = s['wipe']; k = IN_OUT((fr - w0)/(w1 - w0))
        warp = 26*np.sin(hx/130 + fr*.08) + 18*np.sin(hy/90 - fr*.06 + 1.7)            # fabric edge
        if s['b'] == 'summary': field = hy + 2*warp; soft = .12*W/2                     # dusk from the top
        else: field = (W/2 - hx) + 1.5*warp; soft = .08*W/2                             # sweeps in from the right
        if fr < w0: m = np.zeros((H, W), np.float32)
        elif fr >= w1 - 1 and k >= .999: m = np.ones((H, W), np.float32)
        else:
            R = float(np.quantile(field[::3, ::3], k))
            mh = 1 - np.clip((field - R + soft)/(2*soft), 0, 1); mh = mh*mh*(3 - 2*mh)
            m = cv2.resize(mh, (W, H))
        B = plate(s['b'], fr)*GAIN[s['b']]
        out = A*(1 - m[..., None]) + B*m[..., None]
        if 0 < k < 1:
            band = cv2.resize(np.exp(-((field - R)/(.045*W/2))**2), (W, H))
            ca = (band*.28*(1 - k*.6))[..., None]
            out = out*(1 - ca) + (255 - (255 - out)*(255 - B)/255)*ca                     # lit crest in the incoming colour
        cv2.imwrite(f'{WORK}/matte_{s["n"]}/{fr:04d}.png', (m*255).astype(np.uint8))
    cv2.imwrite(f'{WORK}/seq/{fr:04d}.png', dither(out))
    if fr % 50 == 0: print(f'seq {fr}/{N}', flush=True)
ff(['-framerate', str(FPS), '-i', f'{WORK}/seq/%04d.png', *PRORES(3), f'{D}/02-full-sequence-with-wipes/vara-zones-backgrounds-with-wipes.mov'])
ff(['-framerate', str(FPS), '-i', f'{WORK}/seq/%04d.png', '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p', *BT709,
    f'{D}/02-full-sequence-with-wipes/PREVIEW-vara-zones-backgrounds-with-wipes.mp4'])
# full-length mattes (black before, wipe, white after) so each drops in at frame 0
for s in segs:
    if s['kind'] != 'wipe': continue
    n, (w0, w1) = s['n'], s['wipe']; tmp = f'{WORK}/mfull_{n}'; os.makedirs(tmp, exist_ok=True)
    for fr in range(N):
        p = f'{WORK}/matte_{n}/{fr:04d}.png'
        im = cv2.imread(p, 0) if os.path.exists(p) else np.full((H, W), 0 if fr < s['start'] else 255, np.uint8)
        cv2.imwrite(f'{tmp}/{fr:04d}.png', im)
    ff(['-framerate', str(FPS), '-i', f'{tmp}/%04d.png', *PRORES(1),
        f"{D}/02-full-sequence-with-wipes/wipe-mattes/wipe-{n + 1}-{s['a']}-to-{s['b']}_frames-{w0}-{w1 - 1}.mov"])
print('full sequence done', flush=True)

# ---------- per-zone loops (same brightness gains, seamless 10 s) ----------
for z in ([] if SKIP_LOOPS else SEQ):
    tmp = f'{WORK}/loop_{z}'; os.makedirs(tmp, exist_ok=True)
    for i in range(LOOP): cv2.imwrite(f'{tmp}/{i:04d}.png', dither(plate(z, i)*GAIN[z]))
    ff(['-framerate', str(FPS), '-i', f'{tmp}/%04d.png', *PRORES(3), f'{D}/01-zone-background-loops/{NUM[z]}-{z}-background-loop-10s.mov'])
    print('loop', z, flush=True)

# ---------- read me ----------
tc = lambda fr: f'{fr // FPS:02d}:{fr % FPS:02d}'
lines = [f"  {s['a']:>9}{' -> ' + s['b'] if s['kind'] == 'wipe' else '':<14} frames {s['start']:3}-{s['end'] - 1:3}  ({tc(s['start'])}-{tc(s['end'] - 1)})"
         + (f"  wipe {s['wipe'][0]}-{s['wipe'][1] - 1}" if s['kind'] == 'wipe' else '') for s in segs]
open(f'{D}/README.txt', 'w').write(f"""VARA EXPO 2026 teaser: zone backgrounds
All video: 1920x1080, 25 fps, ProRes 422 HQ (mattes ProRes 422 LT), Rec.709, broadcast range. No text, icons or road.

01-zone-background-loops/
  One seamless 10 s loop per zone: 01 Career, 02 Education, 03 Skills, 04 Market, 05 Summary.
  Loop or extend them freely. All four zones are matched in brightness, so your own wipes won't pump.

02-full-sequence-with-wipes/
  vara-zones-backgrounds-with-wipes.mov: all five backgrounds joined by soft fabric wipes ({N} frames, {N / FPS:.2f} s).
  Zones wipe in from the right (each one carries a hint of the next colour on that side); the summary comes
  down from the top. Each wipe is {WIPE_LEN} frames (summary {WIPE_LEN_SUM}), ease in-out, with a soft lit crest.
  wipe-mattes/: the same wipes as full-length luma mattes (black before, white after). Drop in at frame 0 and
  use as a track matte over the loops to rebuild or retime any wipe.
  PREVIEW-*.mp4: H.264 copy for quick viewing.

Timing (seconds:frames):
""" + '\n'.join(lines) + '\n')
print('packaged')
