# Seismic Knowledge Base — Index

Verified against: SEG Wiki, AAPG Wiki, TU Delft OpenCourseWare, GPG, CSEG Recorder  
Last reviewed: 2026-04-20

One paragraph per topic. Follow the link for the full deep dive.

---

## 1. [Seismic Acquisition](seismic_acquisition.md)

A seismic survey fires a controlled sound source (explosion or vibroseis truck) at the surface and records the returning reflected waves using geophones — also at the surface, not buried. Each geophone records a 1D signal (amplitude vs time) called a **trace**: one amplitude value per time sample, sampled every 2–4ms for a window of 1,000–6,000ms. One shot fires; all geophones record simultaneously. The shot truck moves along the survey area firing at regular intervals while the geophone cable follows in large leapfrog jumps (roll-along acquisition). One shot × N geophones = N traces.

---

## 2. [Seismic Processing](seismic_processing.md)

Raw traces are indexed by (shot_x, shot_y, geophone_x, geophone_y, time). Four processing steps convert these into a clean subsurface image: (1) **CMP sort** — group traces by the surface midpoint between shot and geophone; (2) **NMO correction** — flatten the hyperbolic moveout in each CMP gather using the velocity model so traces can be stacked; (3) **Stack** — average traces within each CMP gather, noise cancels, signal reinforces; (4) **Migration** — reposition amplitude from CMP midpoint coordinates to true subsurface reflection point coordinates, sharpening faults and correcting dipping beds. Migration can be poststack (cheap, lower quality) or prestack (120× more expensive, higher quality, preserves AVO).

---

## 3. [The Seismic Volume](seismic_volume.md)

The output of processing is a 3D array `volume[x, y, z] = amplitude`. x and y are **migrated subsurface coordinates** — real geographic positions, not geophone or raw CMP positions. z is **Two-Way Travel Time (TWT)** in milliseconds, not depth in metres (depth conversion requires a separate velocity model step). The array is sliced three ways: inline (fix x), crossline (fix y), timeslice (fix z) — each producing a 2D amplitude image. This is what GeoSAM loads from the SEG-Y file.

---

## 4. [Seismic Attributes](attributes.md)

Attributes are mathematical transforms on a 2D amplitude slice that isolate specific geological signals invisible or ambiguous in raw amplitude. GeoSAM computes four: **envelope** (Hilbert magnitude — reflector strength without polarity), **dip** (Sobel gradient — edges and fault detection), **coherence** (local trace semblance — lateral continuity disruption, best for faults and channels), **texture** (local std dev — lithology heterogeneity). All four stack into a `(H, W, 4)` float32 array.

---

## 5. [SAM Segmentation](sam_segmentation.md)

SAM (Segment Anything Model, Meta 2023) was trained on 1 billion natural images to find closed regions with consistent internal properties bounded by edges — geological features satisfy this naturally. GeoSAM applies SAM zero-shot to 2D seismic slices with no seismic training required. Two modes: **automatic** (grid of prompts, returns all features above IoU/stability thresholds) and **point prompt** (user specifies a pixel location, returns mask for that feature). Validated: bright spot at timeslice 250 detected with IoU=0.987, zero false positives.

---

## 6. [Glossary](glossary.md)

All domain terms in one place: TWT, trace, shot gather, CMP gather, fold, NMO, DMO, stack, migration, RTM, AVO, impedance contrast, bright spot, velocity model, and more.

---

## GeoSAM Pipeline

```
SEG-Y file  (processed, migrated, time-domain 3D volume)
     ↓
load_volume()  →  numpy array (n_il, n_xl, n_t)
     ↓  fix one axis
get_inline / get_crossline / get_timeslice  →  2D slice (H, W)
     ↓
slice_to_rgb()   →  RGB image for SAM
compute_all()    →  (H, W, 4) attribute stack
     ↓
segment_auto() / segment_with_points()  →  list of mask dicts
     ↓
dashboard visualisation
```
