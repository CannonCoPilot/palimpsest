"""Re-render every report plate at high resolution for the click-to-zoom overlay.

House style, matching the report's palette:
  slate  #3A5A6B  every detected box
  rubric #A32B22  the single largest box -- the one frame() anchors on
  amber  #8A6A20  head_y / foot_y and the measure's two verticals
Bespoke recipes are kept for the numbered leaf, the overlap bands and the
contained-pair highlights.
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
Q = int(sys.argv[2]) if len(sys.argv) > 2 else 48
P = Path('witness/plates')
OUT = Path('/private/tmp/claude-501/-Users-nathanielcannon-Claude-Project-Aion/'
           '57a5a9c2-1f51-4222-9923-49c4c39ec11b/scratchpad/fig')

SLATE, RUBRIC, AMBER = '#3A5A6B', '#A32B22', '#8A6A20'
BLUE, ORANGE, GREY = (0, 110, 255), (255, 140, 0), (170, 170, 170)

plates = {p['id']: p for p in json.load(open(P / 'bundle.json'))['plates']}
area = lambda b: max(0., b['x1'] - b['x0']) * max(0., b['y1'] - b['y0'])


def base(pid):
    im = Image.open(P / plates[pid]['img']).convert('RGB')
    im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    return im, ImageDraw.Draw(im), W, im.height


def font(px):
    try:
        return ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', px)
    except Exception:
        return ImageFont.load_default()


def frame_style(pid, name, numbered=False):
    """The default plate: boxes, the anchor box, and the frame it produced."""
    p = plates[pid]
    im, d, w, h = base(pid)
    sw = max(2, round(w / 720 * 2)); sw3 = max(3, round(w / 720 * 3))
    for b in p['boxes']:
        d.rectangle([b['x0'] * w, b['y0'] * h, b['x1'] * w, b['y1'] * h], outline=SLATE, width=sw)
    for y in (p['head_y'], p['foot_y']):
        d.line([0, y * h, w, y * h], fill=AMBER, width=sw)
    for x in p['measure']:
        d.line([x * w, 0, x * w, h], fill=AMBER, width=sw)
    if p['boxes']:
        b = max(p['boxes'], key=area)
        d.rectangle([b['x0'] * w, b['y0'] * h, b['x1'] * w, b['y1'] * h], outline=RUBRIC, width=sw3)
    if numbered:
        f = font(max(11, round(w / 700 * 13)))
        pad = max(13, round(w / 700 * 16))
        for i, b in enumerate(sorted(p['boxes'], key=lambda b: b['y0']), 1):
            x0, y0 = b['x0'] * w, max(0, b['y0'] * h - pad)
            t = str(i)
            tb = d.textbbox((0, 0), t, font=f)
            d.rectangle([x0, y0, x0 + tb[2] + 6, y0 + pad], fill=RUBRIC)
            d.text((x0 + 3, y0), t, fill=(255, 255, 255), font=f)
    save(im, name)


def overlap_bands(pid, name):
    """Partial-overlap defect: every pairwise intersection filled in rubric."""
    p = plates[pid]
    im, d, w, h = base(pid)
    sw = max(2, round(w / 720 * 2))
    bx = p['boxes']
    for b in bx:
        d.rectangle([b['x0'] * w, b['y0'] * h, b['x1'] * w, b['y1'] * h], outline=SLATE, width=sw)
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    n = 0
    for i, a in enumerate(bx):
        for b in bx[i + 1:]:
            x0, y0 = max(a['x0'], b['x0']), max(a['y0'], b['y0'])
            x1, y1 = min(a['x1'], b['x1']), min(a['y1'], b['y1'])
            if x1 <= x0 or y1 <= y0:
                continue
            inter = (x1 - x0) * (y1 - y0)
            if inter >= min(area(a), area(b)) * 0.98:      # containment, not partial
                continue
            od.rectangle([x0 * w, y0 * h, x1 * w, y1 * h], fill=(163, 43, 34, 115),
                         outline=(163, 43, 34, 255), width=sw)
            n += 1
    im = Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB')
    print(f'   {name}: {n} partial-overlap regions')
    save(im, name)


def pair(pid, outer, inner, name):
    """Contained-pair figure: the two boxes in question, everything else muted."""
    im, d, w, h = base(pid)
    sw = max(1, round(w / 720)); sw3 = max(3, round(w / 720 * 3))
    for b in plates[pid]['boxes']:
        hot = b['i'] in (outer, inner)
        d.rectangle([b['x0'] * w, b['y0'] * h, b['x1'] * w, b['y1'] * h],
                    outline=(BLUE if b['i'] == outer else ORANGE) if hot else GREY,
                    width=sw3 if hot else sw)
    save(im, name)


def save(im, name):
    f = OUT / f'{name}.jpg'
    im.save(f, 'JPEG', quality=Q, optimize=True, progressive=True)
    print(f'  {name:12} {im.size[0]}x{im.size[1]}  {f.stat().st_size//1024} KB')


print(f'rendering at width={W} quality={Q}')
for pid, name in [('OT1-1609-P_1011', 'SEV_1011'), ('OT2-1610-P_0749', 'SEV_0749'),
                  ('OT2-1610-P_0821', 'SEV_0821'), ('OT2-1610-P_0024', 'SEV_0024'),
                  ('OT2-1610-P_0026', 'SEV_0026'), ('OT2-1610-P_0035', 'SEV_0035'),
                  ('NT-1582-B_0321', 'SEV_0321'), ('OT2-1610-P_0022', 'CON_0022'),
                  ('OT2-1610-P_0024', 'CON_0024'), ('OT2-1610-P_0668', 'GOOD_0668'),
                  ('OT2-1610-P_1085', 'GOOD_1085'), ('OT1-1609-P_1011', 'E26_BEFORE'),
                  ('OT1-1609-B_0409', 'FRAME_OK')]:
    frame_style(pid, name)
frame_style('OT2-1610-P_0666', 'Q_0666', numbered=True)
overlap_bands('OT2-1610-P_0666', 'PARTIAL')
for pid, o, i, name in [('NT-1582-B_0804', 0, 2, 'DUP_A1'), ('OT1-1609-P_0343', 1, 5, 'DUP_A2'),
                        ('OT2-1610-P_0460', 1, 6, 'DUP_B1'), ('NT-1582-B_0119', 8, 7, 'DUP_C1'),
                        ('OT1-1609-B_0403', 4, 5, 'DUP_C2'), ('OT1-1609-P_0284', 0, 4, 'DUP_C3')]:
    pair(pid, o, i, name)
print('done')
