"""Make frontend/brand-mark.png use a transparent background (remove flat cream/off-white)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "brand-mark.png"


def main() -> int:
    if not SRC.exists():
        print(f"Missing {SRC}", file=sys.stderr)
        return 1
    im = Image.open(SRC).convert("RGBA")
    arr = np.array(im, dtype=np.uint8)
    rgb = arr[:, :, :3].astype(np.float32)
    h, w = rgb.shape[:2]

    # Background colour from image corners (flat frame around logo)
    bands = 8
    top = rgb[:bands, :, :].reshape(-1, 3)
    bot = rgb[-bands:, :, :].reshape(-1, 3)
    left = rgb[:, :bands, :].reshape(-1, 3)
    right = rgb[:, -bands:, :].reshape(-1, 3)
    samples = np.vstack([top, bot, left, right])
    bg = np.median(samples, axis=0)

    dist = np.linalg.norm(rgb - bg.reshape(1, 1, 3), axis=2)

    # Hard transparency inside near-bg region
    hard = dist < 22.0
    soft_hi = 38.0
    soft = (dist >= 22.0) & (dist < soft_hi)

    alpha = arr[:, :, 3].astype(np.float32)
    alpha[hard] = 0.0
    t = (soft_hi - dist[soft]) / (soft_hi - 22.0)
    alpha[soft] = np.clip(alpha[soft] * t, 0.0, 255.0)

    # Trim fully transparent margin (tighter asset, scales bigger in UI)
    out = arr.copy()
    out[:, :, 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    nz = np.argwhere(out[:, :, 3] > 8)
    if len(nz):
        y0, y1 = int(nz[:, 0].min()), int(nz[:, 0].max()) + 1
        x0, x1 = int(nz[:, 1].min()), int(nz[:, 1].max()) + 1
        pad = 2
        y0, x0 = max(y0 - pad, 0), max(x0 - pad, 0)
        y1, x1 = min(y1 + pad, h), min(x1 + pad, w)
        out = out[y0:y1, x0:x1]

    Image.fromarray(out, mode="RGBA").save(SRC, format="PNG", optimize=True)
    print(f"Updated {SRC} ({out.shape[1]}x{out.shape[0]}), transparent background")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
