# Package the render into deliverables for the animator.
#   python3 package.py <bg_root> <render_dir> <deliver_dir>
#
# 01-sections/  one 10 s seamless background loop per zone + the road at rest for that zone (PNG with alpha)
# 02-full/      the whole sequence: background+road, background-only with wipes, road with alpha,
#               a full-length wipe matte per transition, AE pin tracks
# 03-preview/   H.264 copies for quick viewing (one with stand-in titles: review only)
import sys, os, json, subprocess, numpy as np, cv2

BG_ROOT, R, D = sys.argv[1:4]
W, H, FPS, LOOP = 1920, 1080, 25, 250
SCENE = {'career': 'career_warm', 'education': 'education_warm', 'skills': 'skills_warm', 'market': 'market_warm', 'summary': 'finale'}
NUM = {'career': '01', 'education': '02', 'skills': '03', 'market': '04', 'summary': '05'}
timing = json.load(open(f'{R}/timing.json')); N = timing['frames']; segs = timing['segments']
for sub in ['01-sections', '02-full/mattes', '02-full/pin-tracks', '03-preview']: os.makedirs(f'{D}/{sub}', exist_ok=True)
BT709 = ['-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv']
def ff(args): subprocess.run(['ffmpeg', '-v', 'error', '-y', *args], check=True)
PRORES = lambda profile, pix: ['-c:v', 'prores_ks', '-profile:v', str(profile), '-pix_fmt', pix, '-vendor', 'apl0', *BT709]
SCALE = ['-vf', 'scale=out_color_matrix=bt709:out_range=tv']

# ---------- 01 sections: loops (centre of the overscanned plate, 2x up, light dither) + road at rest ----------
rng = np.random.default_rng(3)
for z, scene in SCENE.items():
    tmp = f'{R}/_loop_{z}'; os.makedirs(tmp, exist_ok=True)
    for i in range(LOOP):
        im = cv2.imread(f'{BG_ROOT}/{scene}/{i:04d}.png').astype(np.float32)
        big = cv2.resize(im, (im.shape[1]*2, im.shape[0]*2), interpolation=cv2.INTER_CUBIC)
        ox, oy = (big.shape[1] - W)//2, (big.shape[0] - H)//2
        fr = big[oy:oy + H, ox:ox + W] + rng.uniform(-1, 1, (H, W, 3))
        cv2.imwrite(f'{tmp}/{i:04d}.png', np.clip(fr, 0, 255).astype(np.uint8))
    ff(['-framerate', str(FPS), '-i', f'{tmp}/%04d.png', *SCALE, *PRORES(2, 'yuv422p10le'), f'{D}/01-sections/{NUM[z]}-{z}-background-loop-10s.mov'])
    hold = next(s for s in segs if s['kind'] == 'hold' and s['a'] == z)
    mid = (hold['start'] + hold['end'])//2
    if z != 'summary':
        os.system(f"cp {R}/road/{hold['start']:04d}.png {D}/01-sections/{NUM[z]}-{z}-road-at-rest.png")
    os.system(f"cp {R}/comp/{mid:04d}.png {D}/01-sections/{NUM[z]}-{z}-reference-frame.png")
    print('section', z, flush=True)

# ---------- 02 full ----------
ff(['-framerate', str(FPS), '-i', f'{R}/comp/%04d.png', *SCALE, *PRORES(3, 'yuv422p10le'), f'{D}/02-full/vara-zones-full-background-and-road.mov'])
ff(['-framerate', str(FPS), '-i', f'{R}/bg/%04d.png', *SCALE, *PRORES(2, 'yuv422p10le'), f'{D}/02-full/vara-zones-background-with-wipes.mov'])
ff(['-framerate', str(FPS), '-i', f'{R}/road/%04d.png', *PRORES(4, 'yuva444p10le'), f'{D}/02-full/vara-zones-road-alpha.mov'])
# full-length mattes: black before the wipe, the wipe, white after, so each one drops in at frame 0
for s in segs:
    if s['kind'] != 'move': continue
    n, (w0, w1) = s['n'], s['wipe']; tmp = f'{R}/_matte_{n}'; os.makedirs(tmp, exist_ok=True)
    black, white = np.zeros((H, W), np.uint8), np.full((H, W), 255, np.uint8)
    for f in range(N):
        p = f'{R}/matte_{n}/{f:04d}.png'
        im = cv2.imread(p, 0) if os.path.exists(p) else (black if f < w0 else white)
        cv2.imwrite(f'{tmp}/{f:04d}.png', im)
    name = f"wipe-{n + 1}-{s['a']}-to-{s['b']}_frames-{w0}-{w1 - 1}.mov"
    ff(['-framerate', str(FPS), '-i', f'{tmp}/%04d.png', *PRORES(1, 'yuv422p10le'), f'{D}/02-full/mattes/{name}'])
# AE keyframe data: paste onto a null's Position, parent the icon/title to it
pins = json.load(open(f'{R}/pins.json'))
for z, track in pins.items():
    lines = ['Adobe After Effects 8.0 Keyframe Data', '', f'\tUnits Per Second\t{FPS}', f'\tSource Width\t{W}', f'\tSource Height\t{H}',
             '\tSource Pixel Aspect Ratio\t1', '\tComp Pixel Aspect Ratio\t1', '', 'Transform\tPosition', '\tFrame\tX pixels\tY pixels\tZ pixels\t']
    lines += [f'\t{f}\t{x}\t{y}\t0\t' for f, (x, y) in sorted(((int(k), v) for k, v in track.items()))]
    lines += ['', '', 'End of Keyframe Data', '']
    open(f'{D}/02-full/pin-tracks/{NUM[z]}-{z}-pin-base-position.txt', 'w').write('\n'.join(lines))

# ---------- 03 preview ----------
H264 = ['-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p', *BT709]
ff(['-framerate', str(FPS), '-i', f'{R}/comp/%04d.png', *H264, f'{D}/03-preview/vara-zones-full.mp4'])
ff(['-framerate', str(FPS), '-i', f'{R}/preview/%04d.png', *H264, f'{D}/03-preview/vara-zones-REVIEW-ONLY-stand-in-titles.mp4'])

# ---------- timing sheet ----------
tc = lambda f: f'{f // FPS:02d}:{f % FPS:02d}'
rows = [f"{s['kind']:5} {s['a']:>9} -> {s['b']:<9} frames {s['start']:3}-{s['end'] - 1:3}  ({tc(s['start'])} - {tc(s['end'] - 1)})"
        + (f"   wipe {s['wipe'][0]}-{s['wipe'][1] - 1}" if s['kind'] == 'move' else '') for s in segs]
open(f'{D}/02-full/timing.txt', 'w').write(f'25 fps, {N} frames ({N/FPS:.2f} s). Timecodes are seconds:frames.\n\n' + '\n'.join(rows) + '\n')
print('packaged')
