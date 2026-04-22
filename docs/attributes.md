# Seismic Attributes

← [Back to Knowledge Base Index](seismic_kb.md)

---

## What Attributes Are

Raw seismic amplitude shows everything at once — reflectors, faults, fluids, noise — all superimposed. Attributes are mathematical transforms on a 2D amplitude slice that isolate one specific geological signal, making features that are ambiguous in raw amplitude clearly visible.

GeoSAM computes four attributes. All operate on a 2D slice `(H, W)` and return a 2D array of the same shape. Combined: `compute_all()` returns `(H, W, 4)` float32, one channel per attribute.

---

## 1. Envelope

### What it detects
Reflector **strength** — how large the acoustic impedance contrast is at each point. Independent of polarity (whether the amplitude is positive or negative).

### Why it helps
Raw amplitude alternates red/blue (positive/negative). Envelope collapses that to a single positive value. Fluid anomalies (gas sands, bright spots) show as isolated bright patches. Easier for SAM to find than the raw polarity image.

### Formula
```
analytic_signal = trace + j * hilbert(trace)
envelope        = |analytic_signal|
                = sqrt(real(trace)² + imag(hilbert(trace))²)
```
Applied independently to each column (time axis) of the 2D slice.

### Visual signature
- High envelope (bright) = strong reflection = impedance contrast = possible lithology change or fluid
- Low envelope (dark) = weak reflection = homogeneous rock
- Colormap in dashboard: `plasma` (dark purple → yellow)

---

## 2. Dip

### What it detects
Spatial rate of amplitude change — **edges, boundaries, fault surfaces**. Where amplitude changes fastest laterally, dip is high.

### Why it helps
Faults displace reflectors vertically, creating a sharp lateral amplitude change at the fault surface. This shows up as a bright line in dip even when invisible in raw amplitude. Best single attribute for fault detection.

### Formula
```
Gx = sobel(slice, axis=1)   ← horizontal gradient
Gy = sobel(slice, axis=0)   ← vertical gradient
dip = sqrt(Gx² + Gy²)       ← gradient magnitude
```
Sobel is a standard edge-detection convolution kernel from image processing.

### Visual signature
- High dip (bright) = sharp spatial gradient = fault, channel edge, layer boundary
- Low dip (dark) = smooth homogeneous zone = undisturbed interior of a layer
- Colormap in dashboard: `hot` (black → orange → white)

---

## 3. Coherence

### What it detects
Lateral **continuity** of the seismic signal — how similar adjacent traces are to each other. Disrupted continuity = something disturbed the layering.

### Why it helps
Faults and channels both break lateral continuity and appear as low-coherence zones even when their amplitude contrast is subtle. Most robust attribute for detecting structural discontinuities in noisy data.

### Formula
```
In a 5×5 sliding window:
coherence = 1 - (mean(window)² / mean(window²))
```
This is a local semblance measure. Where all pixels in the window have similar values, the ratio is close to 1 → coherence is close to 0. Where values vary, the ratio is lower → coherence is higher.

Note: high coherence = smooth = 1, low coherence = disrupted = 0. The formula returns values in [0, 1].

### Visual signature
- Low coherence (red in RdYlGn) = disrupted geometry = fault, channel, chaotic zone
- High coherence (green) = smooth undisturbed layering = background shale
- Colormap in dashboard: `RdYlGn` (red=disrupted → green=smooth)

---

## 4. Texture

### What it detects
Local **amplitude variability** — how chaotic or heterogeneous the signal is within a small neighborhood.

### Why it helps
Different rock types have different textural signatures even when their mean amplitude is similar. Background shale (uniform, low texture) is distinguishable from turbidite channel fill (heterogeneous, high texture) or carbonate (high amplitude variability at grain scale).

### Formula
```
In a 5×5 sliding window:
texture = std(window)   ← local standard deviation
```

### Visual signature
- High texture (bright) = chaotic/heterogeneous = channels, turbidites, fractured zones
- Low texture (dark) = smooth/homogeneous = undisturbed background shale
- Colormap in dashboard: `viridis` (dark purple → yellow)

---

## Attribute vs Attribute — What to Use When

| Geological target | Best attribute | Why |
|---|---|---|
| Gas sand / fluid | Envelope | Strips polarity, isolates amplitude anomaly |
| Fault | Dip or Coherence | Dip catches the edge; coherence catches the disruption |
| Channel | Coherence or Texture | Channel disrupts continuity and has distinct internal texture |
| Layer boundaries | Dip | Sobel highlights all boundaries |
| Lithology mapping | Texture | Different facies have different textural character |

---

## GeoSAM Code Reference

```python
from geosam.attributes import (
    compute_envelope,   # (H, W) → (H, W)
    compute_dip,        # (H, W) → (H, W)
    compute_coherence,  # (H, W) → (H, W)
    compute_texture,    # (H, W) → (H, W)
    compute_all,        # (H, W) → (H, W, 4)
    ATTRIBUTE_NAMES,    # ["envelope", "dip", "coherence", "texture"]
)

attrs = compute_all(slice_2d, window=5)
# attrs[:, :, 0] = envelope
# attrs[:, :, 1] = dip
# attrs[:, :, 2] = coherence
# attrs[:, :, 3] = texture
```
