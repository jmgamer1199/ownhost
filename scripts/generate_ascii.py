"""Draws the landscape shown on the computer page (terraced hills, a tree, a moon) as ASCII shading,
like a dithered photo, into ownhost/app/assets/landscape.txt.

    python scripts/generate_ascii.py
"""
import math
import random
from pathlib import Path

W, H = 110, 28
RAMP = " .:-=+*#%@"
random.seed(7)


def noise1(x: float, seed: int) -> float:
    return (math.sin(x * 0.11 + seed) * 0.5 + math.sin(x * 0.037 + seed * 2.3) * 0.8
            + math.sin(x * 0.23 + seed * 0.7) * 0.2)


def ridge(x: int, base: float, amp: float, seed: int, step: int) -> float:
    xs = (x // step) * step  # terraces: blocky, like voxel terrain
    return base - amp * noise1(xs, seed)


img = [[0.0] * W for _ in range(H)]
moon = (W * 0.58, H * 0.24, 6.5)
for y in range(H):
    for x in range(W):
        sky = 0.0
        d = math.hypot((x - moon[0]) * 0.5, y - moon[1])
        if d < moon[2]:
            sky = 0.95 - 0.25 * (d / moon[2]) ** 2
        elif d < moon[2] + 3:
            sky += 0.12 * (1 - (d - moon[2]) / 3)
        if random.random() < 0.012 and y < H * 0.5:
            sky = 0.15
        img[y][x] = sky

layers = [  # far to near: (base row, amplitude, seed, terrace width, brightness top, brightness bottom)
    (H * 0.55, 7, 1, 3, 0.42, 0.22),
    (H * 0.68, 6, 4, 2, 0.62, 0.30),
    (H * 0.82, 4, 9, 2, 0.88, 0.45),
]
for base, amp, seed, step, top, bottom in layers:
    for x in range(W):
        h = int(ridge(x, base, amp, seed, step))
        for y in range(max(h, 0), H):
            depth = (y - h) / max(H - h, 1)
            v = top - (top - bottom) * min(depth * 1.6, 1)
            if y == h:
                v = min(top + 0.12, 1)  # lit edge of each terrace
            img[y][x] = v

# A blocky tree on the nearest hill.
tx = int(W * 0.22)
ground = int(ridge(tx, *layers[2][:3], layers[2][3]))
for y in range(ground - 6, ground):
    for x in (tx, tx + 1):
        img[y][x] = 0.30
for y in range(ground - 13, ground - 5):
    half = 4 if y > ground - 11 else 2
    for x in range(tx - half + 1, tx + half + 1):
        if 0 <= x < W:
            img[y][x] = 0.72 if (x + y) % 3 else 0.55

rows = []
for y in range(H):
    row = []
    for x in range(W):
        v = img[y][x] + ((random.random() - 0.5) * 0.08 if img[y][x] > 0.2 else 0)  # grain, like a dithered photo
        row.append(RAMP[max(0, min(len(RAMP) - 1, int(v * len(RAMP))))])
    rows.append("".join(row).rstrip())
out = Path(__file__).resolve().parent.parent / "ownhost" / "app" / "assets" / "landscape.txt"
out.write_text("\n".join(rows) + "\n", encoding="utf-8")
print(f"Written {out}")
