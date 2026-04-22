# The Seismic Volume

← [Back to Knowledge Base Index](seismic_kb.md)

---

## What the Volume Is

The final output of seismic processing is a 3D array:

```
volume[x, y, z] = amplitude
```

Every cell holds one number — the stacked, migrated amplitude at that location and time.

| Axis | Meaning | Units |
|---|---|---|
| x | Inline index — one horizontal direction across the survey | Array index (maps to metres via survey geometry) |
| y | Crossline index — perpendicular horizontal direction | Array index (maps to metres via survey geometry) |
| z | Time sample index — the vertical axis | Multiply by sampling interval → TWT in milliseconds |
| amplitude | Reflectivity of the subsurface at (x, y, z) | Proportional to impedance contrast between rock layers |

---

## What x, y Actually Represent

This is the most commonly misunderstood point. After the full processing chain:

```
x, y  ≠  geophone positions        (those dissolved during CMP sort)
x, y  ≠  raw CMP midpoint positions (those were before migration)
x, y  =  migrated subsurface coordinates
```

Migration repositions every amplitude value from its CMP midpoint to the true subsurface reflection point. The final x, y in the SEG-Y correspond to real geographic locations in the survey area, tied to real-world coordinates (metres, geographic projection) — if the SEG-Y trace headers were populated correctly during processing.

Without correctly populated headers, you still have a valid amplitude array but it has no geographic reference — just array indices.

---

## What z Represents: Time vs Depth

The z-axis in a standard SEG-Y is **Two-Way Travel Time (TWT)** in milliseconds.

```
z = 0     →  0ms   (shot fires, recording starts)
z = 1     →  4ms   (first sample after shot)
z = 299   →  1196ms (last sample, end of recording window)
```

TWT ≠ depth in metres. A wave at 1000ms TWT could be at 750m depth (slow shale) or 2500m depth (fast carbonate). Converting requires a **velocity model**:

```
depth (m) = TWT (ms) × v(x,y,z) (m/s) / 2
```

Velocity varies with rock type, pressure, fluid content, and depth — it is a 3D field, not a constant. Estimating it accurately is one of the most expensive parts of seismic processing.

### Time domain vs Depth domain

| Domain | z-axis | How obtained |
|---|---|---|
| Time domain | TWT milliseconds | Standard output of time migration |
| Depth domain | Metres | Requires depth migration OR post-hoc depth conversion with velocity model |

Most exploration datasets are delivered in time domain. Depth domain is used for drilling decisions where accurate depth prediction matters.

---

## The Three Slice Types

Fixing one axis gives a 2D image. GeoSAM operates on these 2D slices.

### Inline Slice (fix x)

```
volume[x_fixed, :, :]  →  shape (n_crosslines, n_time)
```

A vertical cross-section running along the crossline direction. Like cutting a loaf of bread — you see the layer structure at one inline position.

```
Crossline →
Time ↓

━━━━━━━━━━━━━━━━━━━━━━  flat reflector
    ╲╲╲╲╲╲╲╲╲╲╲╲╲╲╲    dipping reflector
━━━━━━━━━╲━━━━━━━━━━    fault offset
          ╲
━━━━━━━━━━━━━━━━━━━━━━  deep flat reflector
```

### Crossline Slice (fix y)

```
volume[:, y_fixed, :]  →  shape (n_inlines, n_time)
```

A vertical cross-section running along the inline direction. Perpendicular to the inline slice.

### Timeslice (fix z)

```
volume[:, :, z_fixed]  →  shape (n_inlines, n_crosslines)
```

A horizontal map view at a fixed TWT depth — like a CT scan slice looking down at the subsurface. Shows the geographic extent of features at that depth.

```
Crossline →

Inline ↓    ████████████████████  ← high amplitude (bright spot)
            ████████████████████
            ████████████████████
                    │
              fault line running across map
```

---

## Your Synthetic Dataset

```
Shape: (100, 120, 300)
        │    │    └── 300 time samples × 4ms = 1,200ms TWT
        │    └─────── 120 crossline positions
        └──────────── 100 inline positions

Total cells: 100 × 120 × 300 = 3,600,000
Storage: 3,600,000 × 4 bytes (float32) ≈ 14.4MB + SEG-Y headers = 16.5MB
```

### Built-in features and where to find them

| Feature | Type | Where in volume |
|---|---|---|
| Flat reflectors | Horizontal bands | Inline or crossline, samples 60, 120, 200 |
| Dipping reflector | Tilted band | Crossline slice — dips with crossline direction |
| Fault | Step discontinuity | Crossline slice at y=60 — reflector jumps from sample 90 to 110 |
| Channel | U-shaped amplitude zone | Inline slice around x=50, sample ~180 |
| Bright spot | High amplitude patch | Timeslice z=250, inlines 40–60, crosslines 50–80 |

---

## GeoSAM Code Reference

```python
vol = load_volume("data/synthetic_large.segy")
# vol.shape = (100, 120, 300)

slc = get_inline(vol, 50)      # shape (120, 300) — crossline × time
slc = get_crossline(vol, 60)   # shape (100, 300) — inline × time
slc = get_timeslice(vol, 250)  # shape (100, 120) — inline × crossline

rgb   = slice_to_rgb(slc)      # (H, W, 3) uint8 — for SAM input
attrs = compute_all(slc)       # (H, W, 4) float32 — attribute stack
```
