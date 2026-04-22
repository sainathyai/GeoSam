# SAM Segmentation

← [Back to Knowledge Base Index](seismic_kb.md)

---

## What SAM Is

SAM (Segment Anything Model, Meta 2023) is a foundation model trained on 1 billion natural images to solve one task: given any image and an optional prompt, find closed regions with consistent internal properties separated from their surroundings by an edge.

It was trained on photographs — not seismic data. GeoSAM uses it **zero-shot**: no seismic training data, no fine-tuning required.

### Why it works on seismic

SAM learned a universal concept of "object" — a region that is internally consistent and bounded by a contrast. Geological features satisfy this exactly:

- **Bright spot**: high internal amplitude, bounded by an amplitude edge
- **Channel**: consistent internal texture/amplitude, bounded by reflector edges
- **Fault**: a sharp lateral contrast in the amplitude field

The model cannot tell rock from cat — it just finds regions. Geophysicists interpret what those regions mean.

---

## SAM Architecture (SAM 2.1)

```
Input RGB image (H, W, 3)
         ↓
Image Encoder (Hiera ViT — hierarchical vision transformer)
  extracts features at multiple scales
         ↓
Prompt Encoder
  point coords → positional embeddings
  no prompt    → grid of learned tokens (automatic mode)
         ↓
Mask Decoder
  cross-attention between image features and prompt tokens
  outputs 3 candidate masks at different scales + scores
         ↓
Output: boolean mask (H, W) + predicted_iou + stability_score
```

GeoSAM wraps this so all torch code stays inside `segment.py`. Callers pass numpy arrays, receive numpy arrays.

---

## Input Preparation

SAM expects an RGB image (H, W, 3) with pixel values in [0, 255] uint8.

A seismic slice is a float32 array with values ranging from large negatives to large positives (raw amplitude). `slice_to_rgb()` converts it:

```python
def slice_to_rgb(slice_2d):
    # 1. Clip to 2nd–98th percentile (removes outliers)
    lo, hi = np.percentile(slice_2d, [2, 98])
    clipped = np.clip(slice_2d, lo, hi)
    # 2. Normalise to [0, 1]
    normalised = (clipped - lo) / (hi - lo)
    # 3. Apply RdBu_r colormap (red/blue seismic convention)
    rgb = colormap(normalised)[:, :, :3]  # drop alpha
    # 4. Scale to uint8
    return (rgb * 255).astype(np.uint8)
```

The colormap choice matters: RdBu_r creates colour contrast at zero crossings (reflector boundaries), giving SAM's edge detector clear signals to work with.

---

## Mode 1: Automatic Segmentation

SAM places a regular grid of prompt points across the image. For each point it asks "what object is centred here?" and generates candidate masks.

### Parameters

| Parameter | Default | Effect |
|---|---|---|
| `points_per_side` | 16 | Grid density. 16 → 256 prompt points. Higher = more masks found, slower |
| `pred_iou_thresh` | 0.80 | Minimum SAM confidence. Higher = fewer, more certain masks |
| `stability_score_thresh` | 0.90 | Minimum mask stability. Higher = sharper, more stable boundaries |

### Process

```
1. Generate n×n grid of (x, y) prompt coordinates
2. For each point → 3 candidate masks (small, medium, large scale)
3. Score each mask: predicted_iou, stability_score
4. Discard masks below thresholds
5. Remove duplicate / overlapping masks (NMS)
6. Sort remaining masks by area (largest first)
7. Return list of mask dicts
```

### Output format

```python
masks = segment_auto(rgb, checkpoint, ...)
# masks is a list of dicts, sorted by area descending:
{
    "segmentation":     np.ndarray (H, W) bool,   # which pixels belong to mask
    "area":             int,                        # pixel count
    "predicted_iou":    float,                      # SAM's confidence [0, 1]
    "stability_score":  float,                      # boundary stability [0, 1]
}
```

---

## Mode 2: Point Prompt

User specifies a pixel coordinate (x, y) in the image. SAM returns the best mask for the object at that location.

### When to use
- You know exactly which feature you want
- Automatic mode finds too many masks and the target is buried
- Validating a specific geological feature (e.g. "give me the bright spot mask")

### Process

```
1. Encode (x, y) as a foreground prompt point (label=1)
2. SAM generates 3 candidate masks at different scales
3. Select the mask with the highest predicted_iou
4. Return as a single mask dict
```

### Parameters

```python
mask = segment_with_points(
    rgb,
    point_coords=[(px, py)],   # list of (x, y) pixel coordinates
    checkpoint=ckpt,
    device="cpu",
    point_labels=[1],          # 1=foreground, 0=background
)
# returns (H, W) bool array
```

---

## Interpreting Results

### What predicted_iou means

SAM's internal estimate of how well the mask matches the true object boundary. Trained from the 1B image dataset — not seismic-specific, but still useful as a relative quality signal.

| Score | Interpretation |
|---|---|
| > 0.90 | High confidence. Clean, well-bounded region |
| 0.80–0.90 | Reasonable. Check visually |
| < 0.80 | Low confidence. Treat with caution |

### What stability_score means

Measures whether the mask boundary changes when the threshold is perturbed slightly. Score=1.0 means the boundary is perfectly stable — the region contrast is strong. Score near 0.5 means the boundary is ambiguous.

### Area

Pixel count of the mask. Compare against expected geological feature size:
- Bright spot in synthetic: ~600px at timeslice 250 (20×30 grid cells)
- Large fault zone: could span hundreds of pixels in dip direction

---

## Validated Results on Synthetic Dataset

| Test | Slice | Config | Result |
|---|---|---|---|
| Bright spot detection | Timeslice z=250 | Auto, IoU>0.85 | Single mask, area=600px, IoU=0.987, stability=1.0 |
| Point prompt on bright spot | Timeslice z=250 | Point (65, 50) | Clean mask matching ground truth |
| Fault (raw amplitude) | Timeslice z=100 | Auto | Not detected — insufficient amplitude contrast in time domain |

Fault detection limitation: a 20-sample depth offset doesn't create enough lateral amplitude contrast in a single timeslice after normalization. The dip attribute would catch it (the fault is a clear edge in gradient space). This is expected — different attributes suit different features.

---

## GeoSAM Code Reference

```python
from geosam.sam import segment_auto, segment_with_points

# Automatic mode
masks = segment_auto(
    rgb_image,           # (H, W, 3) uint8
    checkpoint,          # Path to .pt checkpoint file
    device="cpu",
    points_per_side=16,
    pred_iou_thresh=0.80,
    stability_score_thresh=0.90,
)

# Point prompt mode
mask = segment_with_points(
    rgb_image,           # (H, W, 3) uint8
    point_coords=[(x, y)],
    checkpoint=checkpoint,
    device="cpu",
    point_labels=[1],
)
# returns (H, W) bool
```

### Checkpoint → Config mapping (auto-derived in segment.py)

| Checkpoint filename | Parameters | Speed (CPU) |
|---|---|---|
| sam2.1_hiera_tiny.pt | 38M | Fast |
| sam2.1_hiera_small.pt | 46M | Moderate |
| sam2.1_hiera_base_plus.pt | 80M | Slow |
| sam2.1_hiera_large.pt | 224M | Very slow (use GPU) |
