# Seismic Processing

← [Back to Knowledge Base Index](seismic_kb.md)

---

## Overview

Raw field data is indexed by (shot_x, shot_y, geophone_x, geophone_y, time) → amplitude.  
Processing converts this into a clean 3D subsurface image through four steps:

```
Field traces  →  CMP Sort  →  NMO Correction  →  Stack  →  Migration  →  Volume
```

---

## Step 1: CMP Sort (Common Midpoint)

### What it is

For every shot-geophone pair, compute the surface midpoint:

```
midpoint_x = (shot_x + geophone_x) / 2
midpoint_y = (shot_y + geophone_y) / 2
offset     = distance between shot and geophone
```

Sort all traces by midpoint. Traces sharing the same midpoint form a **CMP gather**.

### Why the same midpoints appear naturally

As the shot truck moves, different shot positions combined with different geophone positions produce the same midpoint automatically:

```
Shot at x=0,  Geophone at x=100  →  midpoint=50,  offset=100
Shot at x=25, Geophone at x=75   →  midpoint=50,  offset=50
Shot at x=50, Geophone at x=50   →  midpoint=50,  offset=0
Shot at x=75, Geophone at x=25   →  midpoint=50,  offset=50
```

Four different shots. Four different geophones. All share midpoint=50. Nobody moved to make this happen — it emerges from the geometry of a moving shot with a fixed receiver spread.

### Pre-engineered survey design

Before the survey starts, geophysicists simulate the geometry to guarantee uniform CMP coverage. They choose shot spacing, geophone spacing, and cable length so that every subsurface midpoint is sampled by many shot-geophone pairs (different offsets). This is called **acquisition design**.

### Fold

The number of traces per CMP gather. Typical 3D surveys: 60–120 fold.  
Higher fold → more traces to average → better noise cancellation after stacking.

### The key assumption

CMP assumes flat horizontal layers — all traces in a gather reflect off the same subsurface point directly below the midpoint. This breaks down for dipping reflectors. See DMO below.

---

## Step 2: NMO Correction (Normal Moveout)

### The problem

Within a CMP gather, the same reflector appears at different times for different offsets — farther geophones hear the reflection later because the wave travels a longer path:

```
Offset →  (near)              (far)
Time ↓
            *                         ← near-offset: reflection arrives early
               *           *
                  *     *
                     *                ← far-offset: same reflector, arrives later
```

This traces a hyperbola described by:

```
t(offset)² = t₀² + offset² / v²

t₀     = zero-offset two-way time (what we want)
offset = shot-to-geophone distance
v      = velocity of sound in that rock layer
```

### The correction

NMO applies a time shift to each trace to move it to t₀ — flattening the hyperbola:

```
Δt = t(offset) - t₀   (the NMO correction)

Corrected trace time = t(offset) - Δt = t₀
```

After NMO, all traces in the gather show the same reflector at the same time — they are now stackable.

### Velocity analysis

The velocity v is not known directly. It is estimated from the data by trying many velocity values and finding which one best flattens the hyperbolas — called velocity analysis or velocity picking. The result is a **velocity model** (velocity vs depth for each CMP location).

### DMO (Dip Moveout)

NMO alone fails for dipping reflectors because traces in a CMP gather do not actually reflect from the same subsurface point when dip is present. DMO correction is applied before NMO in these cases to compensate for the dip effect.

---

## Step 3: Stack

After NMO, all traces in a CMP gather are aligned at t₀. Average them:

```
stacked_trace[t] = mean(all NMO-corrected traces in gather at time t)
```

Result: one trace per CMP midpoint. Random noise (incoherent across traces) cancels to zero. The reflector signal (coherent — same t₀ across all traces) reinforces.

**SNR improvement**: proportional to √fold. 100-fold stack improves SNR by 10×.

After stacking, shot and geophone coordinates are gone. Data is now indexed by (midpoint_x, midpoint_y, time) → amplitude. This is the **stacked volume** — an approximation of what the subsurface would look like if you had a shot and geophone at the same location (zero-offset).

---

## Step 4: Migration

### The problem with stacked data

After stacking, amplitude sits at CMP midpoint coordinates. For flat horizontal layers, the midpoint is directly above the reflection point — correct. For dipping reflectors or faults, the reflection point is **laterally displaced** from the midpoint:

```
CMP midpoint M (where amplitude is currently placed)
      │
      │  ← wrong position
      ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  flat: correct
      
         ╲
          ╲  dipping reflector
           ╲
            R  ← true reflection point (off to the side of M)
```

Faults appear as blurry diffraction hyperbolas rather than sharp edges. Dipping beds are at the wrong lateral position.

### What migration does

Migration moves each amplitude value from its CMP coordinate to its **true subsurface reflection point**:

```
Before: amplitude at (midpoint_x, midpoint_y, time)
After:  amplitude at (true_x, true_y, corrected_time)
```

Result: faults sharpen, dipping beds reposition, diffractions collapse to points.

### Migration methods

| Method | Approach | Computational cost | Image quality |
|---|---|---|---|
| Kirchhoff | Ray tracing — traces acoustic rays from surface to each subsurface point | Low | Good for moderate structural complexity |
| Finite Difference | Solves wave equation numerically on a grid | Medium | Better for complex velocity variations |
| RTM (Reverse Time Migration) | Runs the full wave equation backwards in time | Very high | Highest — handles all dip angles, salt bodies |

All methods require a **velocity model**. Migration accuracy is limited by velocity model accuracy regardless of which method is used.

### Poststack vs Prestack Migration

| | Poststack | Prestack |
|---|---|---|
| When applied | After stacking (operates on zero-offset approximation) | Before stacking (each offset gather migrated separately) |
| Image quality | Lower — assumes zero offset | Higher — handles dip and AVO correctly |
| Computation | Cheap | ~120× more expensive (for 120-fold data) |
| AVO preserved | No | Yes |
| Best for | Simple structure, flat layers | Faults, steep dips, fluid detection |

**Industry trend**: GPU compute is making prestack RTM economically viable for mid-size operators. Previously required large on-premise HPC clusters.

---

## Coordinate Transforms Through the Pipeline

| Stage | x, y meaning |
|---|---|
| Field recording | Shot position AND geophone position (two separate coords) |
| After CMP sort | Midpoint = (shot + geophone) / 2 |
| After stack | Same as midpoint |
| After migration | **True subsurface reflection point** — geometrically correct |
| In SEG-Y file | Migrated coordinates, georeferenced to real geography (if trace headers populated) |

The final volume x, y are **neither geophone positions nor CMP positions**. They are migrated positions. This is what GeoSAM receives. See [The Seismic Volume](seismic_volume.md).
