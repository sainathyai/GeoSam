"""
Generate a realistic synthetic SEG-Y for development and testing.

Creates a 100x120x300 volume (inlines x crosslines x samples) with:
  - Background layered reflectors (flat and dipping)
  - A fault (lateral discontinuity)
  - A channel (U-shaped low-amplitude zone)
  - A bright spot (high-amplitude anomaly, mimics gas sand)
  - Band-limited noise

This gives every attribute (envelope, dip, coherence, texture) something
to respond to, and gives SAM recognisable boundary shapes to segment.

Run from geosam project root:
    python scripts/generate_test_segy.py
"""

import numpy as np
import os, sys
import importlib.util

# Windows DLL fix before importing segyio
if sys.platform == "win32":
    spec = importlib.util.find_spec("segyio")
    if spec:
        os.add_dll_directory(os.path.dirname(spec.origin))

import segyio

from pathlib import Path

OUTPUT      = Path(__file__).parent.parent / "data" / "synthetic_large.segy"
N_INLINES    = 100
N_CROSSLINES = 120
N_SAMPLES    = 300
SAMPLE_RATE  = 4   # ms

rng = np.random.default_rng(42)

# ── 1. Build amplitude model in depth (sample) space ─────────────────────────
volume = np.zeros((N_INLINES, N_CROSSLINES, N_SAMPLES), dtype=np.float32)

def ricker(n_samples, peak_freq=30, dt=0.004):
    """Ricker wavelet — the standard seismic test signal."""
    t = (np.arange(n_samples) - n_samples // 2) * dt
    pft2 = (np.pi * peak_freq * t) ** 2
    return ((1 - 2 * pft2) * np.exp(-pft2)).astype(np.float32)

wavelet = ricker(41)

def add_reflector(vol, depth_fn, amplitude, width=3):
    """Stamp a reflector at depth defined by depth_fn(il, xl)."""
    for il in range(N_INLINES):
        for xl in range(N_CROSSLINES):
            d = int(depth_fn(il, xl))
            d = np.clip(d, 20, N_SAMPLES - 60)
            vol[il, xl, d - width : d + width] += amplitude

# Flat reflectors
add_reflector(volume, lambda il, xl: 60,  amplitude=3000)
add_reflector(volume, lambda il, xl: 120, amplitude=2000)
add_reflector(volume, lambda il, xl: 200, amplitude=1500)

# Dipping reflector (dips with crossline)
add_reflector(volume, lambda il, xl: 150 + xl * 0.4, amplitude=1800)

# Faulted reflector — same flat reflector but offset after crossline 60
add_reflector(
    volume,
    lambda il, xl: 90 if xl < 60 else 110,
    amplitude=2500,
)

# ── 2. Channel: lower amplitude U-shape around inline 50 ──────────────────────
for il in range(N_INLINES):
    dist_from_centre = abs(il - 50)
    if dist_from_centre < 20:
        # Channel axis at sample 180, walls at 160 and 200
        channel_depth = int(180 - (20 - dist_from_centre) * 0.8)
        volume[il, :, channel_depth - 5 : channel_depth + 5] += (
            800 * (1 - dist_from_centre / 20)
        )

# ── 3. Bright spot (gas sand proxy) — high amplitude patch ────────────────────
volume[40:60, 50:80, 245:258] += 5000

# ── 4. Convolve each trace with Ricker wavelet for realism ────────────────────
from scipy.signal import fftconvolve

for il in range(N_INLINES):
    for xl in range(N_CROSSLINES):
        volume[il, xl] = fftconvolve(volume[il, xl], wavelet, mode="same")

# ── 5. Add band-limited noise ─────────────────────────────────────────────────
noise = rng.standard_normal(volume.shape).astype(np.float32)
from scipy.ndimage import gaussian_filter
noise = gaussian_filter(noise, sigma=(0, 0, 1.5))   # smooth in time only
volume += noise.astype(np.float32) * 150

# ── 6. Write SEG-Y ────────────────────────────────────────────────────────────
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

spec = segyio.spec()
spec.sorting = segyio.TraceSortingFormat.INLINE_SORTING
spec.format  = segyio.SegySampleFormat.IEEE_FLOAT_4_BYTE
spec.samples = np.arange(N_SAMPLES, dtype=np.float32) * SAMPLE_RATE
spec.ilines  = np.arange(1, N_INLINES + 1)
spec.xlines  = np.arange(1, N_CROSSLINES + 1)

with segyio.create(str(OUTPUT), spec) as f:
    f.bin.update(tsort=segyio.TraceSortingFormat.INLINE_SORTING)
    tr = 0
    for il in spec.ilines:
        for xl in spec.xlines:
            f.header[tr] = {
                segyio.TraceField.INLINE_3D:    int(il),
                segyio.TraceField.CROSSLINE_3D: int(xl),
            }
            f.trace[tr] = volume[il - 1, xl - 1, :]
            tr += 1

print(f"Written:    {OUTPUT}")
print(f"Shape:      {N_INLINES} inlines x {N_CROSSLINES} crosslines x {N_SAMPLES} samples")
print(f"File size:  {OUTPUT.stat().st_size / 1024 / 1024:.1f} MB")
print(f"Features:   flat reflectors, dipping layer, fault at XL=60, channel at IL=50, bright spot")
