# GeoSAM — Product Requirements Document

**Version:** 1.0  
**Date:** 2026-04-12  
**Author:** Sainatha Yatham  
**Status:** Pre-build planning

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Why This Project, Why Now, Why You](#3-why-this-project-why-now-why-you)
4. [What We Are Building](#4-what-we-are-building)
5. [Users](#5-users)
6. [Core Concepts You Must Understand](#6-core-concepts-you-must-understand)
7. [Functional Requirements](#7-functional-requirements)
8. [Technical Architecture](#8-technical-architecture)
9. [Data Sources](#9-data-sources)
10. [Component Deep Dives](#10-component-deep-dives)
11. [API Design](#11-api-design)
12. [Non-Functional Requirements](#12-non-functional-requirements)
13. [Tech Stack with Rationale](#13-tech-stack-with-rationale)
14. [Implementation Phases](#14-implementation-phases)
15. [Success Metrics](#15-success-metrics)
16. [Risks and Mitigations](#16-risks-and-mitigations)
17. [Out of Scope](#17-out-of-scope)

---

## 1. Executive Summary

GeoSAM is an open source Python toolkit that brings Meta's Segment Anything Model (SAM2) to seismic interpretation. It implements and extends the methodology published in AAPG March 2026 ("Human Insight with Machine Precision for Clearer Geology") into a production-quality, pip-installable package with an interactive UI, reproducible experiment tracking, and proper software engineering practices.

The core insight: SAM2 was trained on over 1 million natural images and understands the concept of edges and boundaries without ever seeing geological data. A seismic interpreter can click on a channel in a time slice and SAM2 will snap to its boundaries in seconds — no training data, no labeled examples, zero-shot.

GeoSAM makes this accessible. The original research produced a Python prototype. GeoSAM produces a tool the geoscience community can actually install and use.

---

## 2. Problem Statement

### The interpreter's daily reality

A seismic interpreter working on a 3D survey might look at 300–600 time slices, each containing geological features — channels, faults, reefs, karst structures — that must be identified, bounded, and mapped. This is done mostly by hand. The interpreter draws polygons around features, one slice at a time.

For a complex channel system across 300 slices, this can take days of focused work. The process is:
- **Tedious** — the same motion repeated hundreds of times
- **Inconsistent** — fatigue degrades quality over time, different interpreters draw boundaries differently
- **Not scalable** — bigger surveys mean proportionally more manual work

### The machine learning catch-22

Traditional ML solutions require training data: hundreds of hand-labeled seismic examples per feature type, per survey, per geological setting. The labels are expensive to produce (an expert's time), and the model trained on one survey often fails on another because geological character varies.

This is the bottleneck. You cannot use traditional supervised ML without first solving the labeling problem, and the labeling problem is what you need ML to solve in the first place.

### What the research showed

The AAPG 2026 paper demonstrated that a foundation model (SAM2) trained entirely on natural images can identify geological boundaries in seismic data without any geological training data. It generalizes because edges are edges — the physics of boundaries does not change between a photograph of a river and a seismic amplitude map of a submarine channel.

But the paper produced a research prototype. The geoscience community needs a proper tool.

---

## 3. Why This Project, Why Now, Why You

### Why this project

The technique works. The paper validates it. What does not exist yet is:
- A pip-installable package the community can use
- Support for multiple public seismic datasets out of the box
- An interactive UI for non-programmers
- Experiment tracking to compare attribute combinations systematically
- Proper tests, CI/CD, and documentation

Building the production version of a validated research idea is a well-understood path to community impact and visibility.

### Why now

The paper was published March 2026. The window to be the person who built the community tool is narrow — if this space remains unaddressed for 6–12 months, someone else will fill it. Being early matters in open source.

### Why you specifically

- **8 years at Borehole Seismic LLC** — you have seen seismic data daily. You know what a channel looks like, what a fault termination looks like, why the 06:00 UTC SLA matters. You are not guessing at domain context.
- **MS in Computer Engineering, thesis in Imaging Systems** — image segmentation is your graduate research area. SAM is a segmentation model. This is not a stretch, it is a direct application.
- **Veritas Seismic** — you are running AI on microseismic data commercially right now. This is your third project in the geoscience AI space, not your first.
- **The AAPG/SEG community** — these communities are actively looking for practitioners who can bridge geophysics and modern AI tooling. Most ML engineers cannot speak the geology. Most geologists cannot build software properly. You can do both.

---

## 4. What We Are Building

### The one-sentence version

A Python package that lets a seismic interpreter click on a geological feature in a time slice and get back precise boundaries, clustered facies maps, and exportable geobodies — without any training data.

### The full picture

GeoSAM is three things in one:

**1. A Python library (`pip install geosam`)**
Clean, well-tested, well-documented Python package. Import it, load a SEG-Y file, compute attributes, run SAM2, run SOM, export results. All scriptable. All composable. Designed for researchers and engineers who want to build on it.

**2. An interactive Gradio application**
A browser-based UI. Upload a SEG-Y file (or select a public dataset), scrub through time slices with a slider, click on features, get SAM2 segmentation in real time. No code required. Designed for geologists and interpreters who do not program.

**3. An MLflow experiment tracker**
Every run logged: which attributes were used, what SOM configuration, what the resulting clustering quality was. Compare runs. Identify which attribute combination gives the best channel separation. Export reproducible configs.

### What the workflow looks like end to end

```
1. Load SEG-Y seismic volume
         ↓
2. Compute 5 seismic attributes
   (dip, energy ratio, coherent energy, GLCM homogeneity, spectral)
         ↓
3. Extract time slice as RGB image
         ↓
4. Interpreter clicks on a channel → point prompt sent to SAM2
         ↓
5. SAM2 generates:
   - Binary mask (where the channel is: 1 or 0 per pixel)
   - Logits (confidence map: how sure SAM is per pixel, continuous)
         ↓
6. Logits added as a 6th attribute alongside the 5 seismic attributes
         ↓
7. All 6 attributes fed into SOM (Self-Organizing Map)
   SOM clusters similar attribute combinations together
         ↓
8. Result: facies map — channel vs non-channel, sand vs mud, etc.
   With sharper boundaries and better facies separation than without SAM
         ↓
9. SAM masks used to extract channel geometry across all time slices
   → geobody (3D shape of the channel system)
         ↓
10. Export: masks as .npy, geobody as .vtk (opens in ParaView/Petrel)
```

---

## 5. Users

### Primary: Seismic Interpreter / Geophysicist

**Who they are:** Works at an oil company, exploration firm, or consulting company. Interprets 3D seismic surveys to find hydrocarbons or characterize reservoirs. Uses software like Petrel (Schlumberger), Kingdom, or OpendTect daily.

**Their problem:** Manual interpretation of large surveys takes too long. They want to speed up channel mapping and facies classification without learning to code or training ML models.

**What they need from GeoSAM:**
- Load their SEG-Y file (the industry standard format)
- Point and click to delineate features
- Get results that match their geological judgment
- Export results in formats their existing software accepts

**Their technical level:** Not a programmer. Knows their geology deeply. Will use the Gradio UI. Will not read source code.

### Secondary: Geoscience ML Researcher

**Who they are:** PhD student or research scientist at a university or national lab. Working on applying ML to geophysics. Reads papers like the AAPG 2026 article.

**Their problem:** Wants to experiment with SAM-based approaches but does not want to reimplement the data pipeline from scratch. Needs a solid baseline to build on.

**What they need from GeoSAM:**
- Clean Python API they can import and extend
- Support for multiple benchmark datasets (F3, Parihaka, Penobscot)
- MLflow integration to track experiments reproducibly
- A baseline they can compare new methods against

**Their technical level:** Comfortable with Python, PyTorch, and Jupyter notebooks. Will read the source code. Will submit issues and possibly PRs.

### Tertiary: MLOps / AI Engineer (portfolio context)

**Who they are:** You, presenting this project in job interviews and on GitHub.

**What you need:**
- A clean, well-engineered codebase that demonstrates software quality
- Reproducible experiments that demonstrate ML rigor
- A community that has adopted and validated the tool
- A story that connects domain expertise, ML knowledge, and software engineering

---

## 6. Core Concepts You Must Understand

Before building, you need to understand these concepts deeply enough to explain them in an interview without notes.

### 6.1 SEG-Y Format

SEG-Y (Society of Exploration Geophysicists Y format) is the standard file format for seismic data. Think of it as the DICOM of geophysics.

A 3D seismic dataset is a cube of numbers. Each number represents the amplitude of a seismic wave reflection at a specific location (inline, crossline) and time (milliseconds). The cube has three dimensions:
- **Inline:** rows of receivers, one direction
- **Crossline:** perpendicular direction
- **Time (or depth):** how far the wave traveled before bouncing back

A **time slice** is a horizontal cut through this cube at a fixed time value. It shows you the seismic character of the subsurface at a specific depth. Channels, faults, and other geological features appear as patterns in the amplitude.

The Python library `segyio` reads SEG-Y files into numpy arrays. You will use it like this:

```python
import segyio
import numpy as np

with segyio.open("f3.sgy", iline=189, xline=193) as f:
    data = segyio.tools.cube(f)  # returns (n_inlines, n_crosslines, n_samples) array
```

### 6.2 Seismic Attributes

Raw seismic amplitude is just one way to look at the data. Seismic attributes are mathematical transformations of the amplitude that highlight different geological features. Think of them like image filters — each reveals different structure.

**The five attributes used in the paper:**

| Attribute | What it measures | What it highlights |
|-----------|-----------------|-------------------|
| Dip | Rate of change in reflector inclination (Sobel gradient) | Structural dipping features, faults |
| Energy Ratio | Ratio of trace energy to local average | Bright spots, channel edges |
| Coherent Energy | Energy within coherent (laterally continuous) reflections | Edges of discontinuities |
| GLCM Homogeneity | Gray-Level Co-occurrence Matrix texture measure | Internal architecture, facies texture |
| Peak Spectral Freq/Magnitude | Dominant frequency and its amplitude (via CWT) | Thin beds, sand vs shale |

Each attribute is computed per-sample across the volume, producing a separate 3D cube the same size as the original. For SOM, you stack these into a feature matrix: each sample gets a vector of [amplitude, dip, energy_ratio, coherent_energy, glcm_homogeneity, spectral_freq, spectral_mag].

### 6.3 Segment Anything Model (SAM2)

SAM2 is a foundation model released by Meta in 2024. It was trained on:
- SA-1B dataset: 1 billion masks across 11 million natural images
- SA-V dataset: video segmentation data

It has two key capabilities:

**Zero-shot image segmentation:** Given any image and a prompt (point click, bounding box, or text), it segments the object. It has never seen seismic data but it understands edges and boundaries universally.

**Video object tracking:** Given a first-frame prompt, it can track an object across subsequent frames using a memory mechanism. For seismic: prompt on one time slice, track the channel across all subsequent slices.

**How SAM2 works internally (simplified):**
1. Image Encoder (ViT-based): converts the input image to feature embeddings
2. Prompt Encoder: converts point/box prompts to embeddings
3. Mask Decoder: cross-attends image features and prompt features → produces masks and logits

**Masks vs Logits:**
- **Mask:** Binary output. Each pixel is 0 (not the feature) or 1 (is the feature).
- **Logits:** Raw output before binarization. Each pixel has a continuous score. High logit = SAM is confident this pixel is part of the feature. Low logit = confident it is not. Near-zero = uncertain.

The paper's key insight: treat logits as a seismic attribute. They carry more information than binary masks because they encode SAM's confidence gradient, which aligns with geological boundary gradients.

### 6.4 Self-Organizing Maps (SOM)

SOM is an unsupervised neural network algorithm from 1982 (Kohonen). It takes a high-dimensional feature matrix and produces a 2D map where similar data points are placed near each other.

For seismic: give it N samples, each described by 6-8 attribute values. It learns a 2D grid (say 10×10 = 100 nodes) where each node represents a prototype attribute vector. Each input sample is assigned to its closest node.

**Why SOM for seismic:**
- No labels needed — unsupervised
- Preserves topology: similar facies end up as adjacent clusters
- Results are visually interpretable: each node = a geological facies
- Standard in the geophysics industry for decades — interpreters trust it

**The GeoSAM improvement:** Standard SOM on seismic attributes produces noisy cluster boundaries because attributes alone do not sharply separate channel edges. Adding SAM logits as an extra attribute gives the SOM "guide rails" — it puts more weight on the channel boundaries that SAM already identified. Result: sharper clusters, better facies separation.

### 6.5 Geobodies

A geobody is a 3D representation of a geological feature extracted from the seismic volume. It is the output you hand to a reservoir engineer: "here is the shape of the channel, here is its volume, here is how it connects vertically."

In GeoSAM, a geobody is built by:
1. Running SAM on each time slice → binary mask per slice
2. Stacking all masks into a 3D boolean volume
3. Labeling connected 3D regions (scipy.ndimage.label)
4. Exporting the largest connected component as a .vtk file

.vtk files open in ParaView (free, open source) or can be imported into Petrel and Kingdom.

---

## 7. Functional Requirements

### Must Have (v0.1.0)

| ID | Requirement |
|----|------------|
| F01 | Load SEG-Y files and extract inline, crossline, and time slices as numpy arrays |
| F02 | Compute all 5 seismic attributes (dip, energy ratio, coherent energy, GLCM homogeneity, peak spectral) |
| F03 | Run SAM2 on a 2D time slice with point prompts, return masks and logits |
| F04 | Batch-process all time slices, returning per-slice masks and logits |
| F05 | Combine seismic attributes + SAM logits into SOM feature matrix |
| F06 | Train SOM and assign cluster IDs to every sample in the volume |
| F07 | Log all experiment parameters and metrics to MLflow |
| F08 | Gradio UI: load dataset, display time slice, accept point prompts, show SAM output |
| F09 | Export masks as numpy .npy arrays |
| F10 | Export geobodies as .vtk files |
| F11 | Support F3 Netherlands dataset (download instructions + loader) |
| F12 | Docker container for running the Gradio UI without local setup |

### Should Have (v0.2.0)

| ID | Requirement |
|----|------------|
| F13 | Support Parihaka and Penobscot datasets |
| F14 | Box prompt support (draw a rectangle to prompt SAM) |
| F15 | Cross-slice tracking using SAM2 video mode |
| F16 | Cluster quality metrics (silhouette score, Davies-Bouldin) |
| F17 | PyPI package (`pip install geosam`) |
| F18 | MkDocs documentation site |

### Won't Have (v0.1.0)

- Training or fine-tuning any model (that is Nexus)
- Petrel plugin (requires Schlumberger SDK agreement)
- Fault interpretation (different problem, future scope)
- Depth conversion (requires velocity model, out of scope)

---

## 8. Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GRADIO UI (browser)                       │
│  Dataset selector · Slice slider · Click prompt · Export    │
└──────────────────────────┬──────────────────────────────────┘
                           │ function calls
┌──────────────────────────▼──────────────────────────────────┐
│                  geosam Python package                       │
│                                                              │
│  ┌─────────┐   ┌────────────┐   ┌────────────┐             │
│  │   io/   │   │ attributes/│   │segmentation│             │
│  │ segy.py │──▶│ pipeline.py│──▶│sam_runner  │             │
│  └─────────┘   └────────────┘   └─────┬──────┘             │
│                                        │ masks + logits      │
│                               ┌────────▼──────┐             │
│                               │ clustering/   │             │
│                               │    som.py     │             │
│                               └────────┬──────┘             │
│                                        │ cluster IDs         │
│                               ┌────────▼──────┐             │
│                               │    viz/       │             │
│                               │ geobody.py    │             │
│                               └───────────────┘             │
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │  tracking/mlflow_logger.py                        │       │
│  │  Logs: params, metrics, attribute maps, cluster   │       │
│  │  maps, model checkpoints                          │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                           │
             ┌─────────────▼──────────────┐
             │       MLflow Server         │
             │  (runs locally in Docker)   │
             └─────────────────────────────┘
```

---

## 9. Data Sources

### F3 Netherlands (Primary development dataset)

- **What it is:** 3D seismic survey from the Dutch North Sea, shot in the late 1980s
- **Why it is the benchmark:** Freely available, widely used in geoscience ML research, well-understood geology, multiple channel systems visible
- **Size:** ~1 GB
- **Format:** SEG-Y
- **Download:** OpendTect Data Repository (open-data.opendtect.org) — free registration required
- **Geology:** Deltaic and fluvial channel systems, clear in time slices around 500–800ms TWT

### Parihaka New Zealand (Secondary)

- **What it is:** 3D seismic survey from New Zealand's Taranaki Basin
- **Why:** Same geological province as Canterbury Basin referenced in the paper, complex stratigraphy
- **Size:** ~2 GB
- **Download:** New Zealand Petroleum & Minerals public database (nzpam.govt.nz)

### Penobscot Nova Scotia (Tertiary)

- **What it is:** 3D survey from the Scotian Basin, Atlantic Canada
- **Why:** Carbonate features, different geological character than F3, tests generalization
- **Size:** ~1 GB
- **Download:** dGB Earth Sciences public repository

### Synthetic test data (for CI/CD)

Generate a minimal synthetic SEG-Y in tests/fixtures/ — a 50×50×200 cube of random noise with a synthetic channel pattern added. Small enough to run in GitHub Actions, large enough to test the full pipeline.

---

## 10. Component Deep Dives

### 10.1 SEG-Y I/O (`geosam/io/segy.py`)

The hardest part of working with seismic data is I/O, not ML. SEG-Y files have:
- A 3200-byte text header (EBCDIC encoding — an IBM mainframe format from the 1960s)
- A 400-byte binary header
- Per-trace binary headers
- Trace data in varying word formats (IBM float, IEEE float, 2-byte int)

`segyio` handles all of this. Your job is to build a clean wrapper that returns numpy arrays in a consistent format.

Key design decision: **standardize the axis order** to (inline, crossline, time) everywhere. This is not guaranteed from segyio and different surveys have different header conventions. Enforce it at load time.

```python
def load_volume(path: str) -> np.ndarray:
    """Returns (n_inlines, n_crosslines, n_samples) float32 array."""

def extract_time_slice(volume: np.ndarray, time_idx: int) -> np.ndarray:
    """Returns (n_inlines, n_crosslines) float32 array."""

def normalize_for_sam(slice_2d: np.ndarray) -> np.ndarray:
    """
    SAM2 expects (H, W, 3) uint8 [0-255].
    Seismic amplitudes are float32, often in [-10000, 10000] range.
    Steps: clip outliers (p2/p98) → min-max normalize → convert to uint8 → replicate to RGB.
    """
```

### 10.2 Attribute Computation (`geosam/attributes/`)

**Dip attribute:**
The structural dip measures how steeply the reflectors are inclined. Computed as the magnitude of the gradient in the inline and crossline directions.

```python
from scipy.ndimage import sobel

def compute_dip(volume: np.ndarray) -> np.ndarray:
    grad_il = sobel(volume, axis=0)   # inline gradient
    grad_xl = sobel(volume, axis=1)   # crossline gradient
    dip = np.sqrt(grad_il**2 + grad_xl**2)
    return dip
```

**GLCM Homogeneity:**
Gray-Level Co-occurrence Matrix is a texture descriptor. Homogeneity measures how similar adjacent pixel values are. In seismic: channels have chaotic internal texture (low homogeneity) while surrounding shales are more uniform (high homogeneity). Computed per time slice using `skimage.feature.graycomatrix` and `graycoprops`.

**Peak Spectral Attributes:**
Use a Continuous Wavelet Transform (CWT) to decompose each trace into frequency components. The peak frequency is where the energy is concentrated. Thin sand beds have higher peak frequencies than thick shales. Computed using `scipy.signal.cwt`.

**Pipeline design:** All five attributes computed in a single pass through `compute_all(volume)`, returned as a dict. The dict keys become MLflow parameter names. This makes it easy to exclude or add attributes for experiments.

### 10.3 SAM2 Integration (`geosam/segmentation/sam_runner.py`)

SAM2 is used in image mode (single slice) or video mode (track across slices).

**Image mode workflow:**
```
1. Load SAM2 model from checkpoint (sam2_hiera_large.pt — best accuracy)
2. Set image: predictor.set_image(slice_rgb)  # (H, W, 3) uint8
3. Predict: masks, scores, logits = predictor.predict(
       point_coords=np.array([[x, y]]),
       point_labels=np.array([1]),  # 1 = foreground
       multimask_output=True,       # returns 3 masks at different granularities
   )
4. Select best mask by score
5. Return: mask (H, W) bool, logit (H, W) float32
```

**Logit handling:**
The raw logit output from SAM2 has the same spatial resolution as the input image. Values range roughly from -10 to +10. Sigmoid(logit) gives probability. For use as seismic attribute: normalize to [0, 1] range using sigmoid, then scale to match other attribute ranges.

**Batch processing design:**
Processing 300 slices sequentially is slow. Use `concurrent.futures.ThreadPoolExecutor` to parallelize — SAM2's image encoder can process independent images in parallel on GPU. Target: <5 minutes for 300 slices on a single A10G GPU.

### 10.4 SOM Clustering (`geosam/clustering/som.py`)

MiniSOM is a pure-Python SOM implementation. The key parameters:

| Parameter | Default | Effect |
|-----------|---------|--------|
| grid_x | 10 | SOM width — more nodes = finer clustering |
| grid_y | 10 | SOM height |
| sigma | 1.5 | Initial neighborhood radius — higher = more spatial smoothing |
| learning_rate | 0.5 | Initial learning rate |
| iterations | 5000 | Training steps — more = better convergence |

**Feature matrix construction:**
```python
# For each sample (each pixel in each time slice):
features = np.stack([
    amplitude.ravel(),
    dip.ravel(),
    energy_ratio.ravel(),
    coherent_energy.ravel(),
    glcm_homogeneity.ravel(),
    spectral_freq.ravel(),
    spectral_mag.ravel(),
    sam_logits.ravel(),   # the SAM contribution — this is the key improvement
], axis=1)

# Normalize to [0, 1] per feature — required for SOM
scaler = MinMaxScaler()
features_scaled = scaler.fit_transform(features)
```

**MLflow experiment logging:**
Run the SOM twice — once without SAM logits (baseline), once with SAM logits (improved). Log both runs. The silhouette score improvement between runs is your key result. This is reproducible evidence that SAM logits improve clustering, not just a visual claim.

---

## 11. API Design

### Python API (public interface)

```python
import geosam

# Load data
volume = geosam.io.load_volume("f3.segy")
slice_2d = geosam.io.extract_time_slice(volume, time_idx=150)

# Compute attributes
attrs = geosam.attributes.compute_all(volume)
# returns: {"dip": np.ndarray, "energy_ratio": ..., ...}

# Run SAM
sam = geosam.SeismicSAM(checkpoint="sam2_hiera_large")
result = sam.segment_slice(
    slice_rgb=geosam.io.normalize_for_sam(slice_2d),
    point_coords=[(120, 85)],
    point_labels=[1],
)
# result: {"mask": np.ndarray, "logit": np.ndarray, "score": float}

# Cluster with SOM
som = geosam.SeismicSOM(grid_x=10, grid_y=10)
som.fit(volume, attrs, sam_logits=result["logit"])
cluster_map = som.predict(volume, attrs, sam_logits=result["logit"])
# cluster_map: (n_inlines, n_crosslines, n_time) int array

# Export
geosam.export.mask_to_npy(result["mask"], "channel_mask.npy")
geosam.export.cluster_map_to_vtk(cluster_map, "facies_map.vtk")
```

### Gradio UI inputs/outputs

```
Inputs:
  - dataset: dropdown (F3, Parihaka, Penobscot, Upload)
  - segy_file: file upload (if Upload selected)
  - time_slice_idx: slider (0 to n_slices-1)
  - attribute_overlay: dropdown (None, Dip, Energy Ratio, ...)
  - sam_checkpoint: dropdown (sam2_hiera_tiny, sam2_hiera_large)
  - som_grid_size: slider (5×5 to 20×20)
  - run_som: checkbox

Outputs:
  - slice_image: image (seismic amplitude)
  - sam_overlay: image (mask overlaid on amplitude)
  - logit_heatmap: image (SAM confidence map)
  - som_cluster_map: image (colored cluster assignments)
  - metrics_table: dataframe (silhouette score, n_clusters, runtime)
  - download_masks: file download
  - download_geobody: file download
```

---

## 12. Non-Functional Requirements

| Category | Requirement |
|----------|------------|
| Performance | Process a 300-slice time volume in < 10 minutes on a machine with a single GPU (A10G or equivalent) |
| Performance | SAM inference on a single time slice < 3 seconds (including image encoding) |
| Installability | `pip install geosam` works on Python 3.10+ on Linux, macOS, Windows |
| Reproducibility | Any experiment run can be reproduced exactly by replaying its MLflow parameters |
| Test coverage | Core library functions (io, attributes, sam_runner, som) covered by unit tests |
| Documentation | Every public function has a docstring. README has quickstart, dataset download guide, and at least 3 example outputs |
| Containerization | `docker run geosam/app` launches the Gradio UI with no additional setup |

---

## 13. Tech Stack with Rationale

| Component | Choice | Why not the alternative |
|-----------|--------|------------------------|
| SEG-Y I/O | `segyio` | Industry standard, maintained by Equinor. Alternative: `obspy` is for earthquake seismology, not exploration. |
| SAM model | `segment-anything-2` (Meta) | SAM2 has video tracking across slices. SAM1 does not. MobileSAM is too small for complex geological boundaries. |
| Attribute computation | `scipy`, `scikit-image`, `bruges` | `bruges` is the Python geophysics library — built exactly for this. `scipy` for CWT. `skimage` for GLCM. |
| SOM | `minisom` | Pure Python, no C dependencies, easy to install. Alternative `somoclu` requires MPI compilation. |
| Experiment tracking | `mlflow` | Open source, self-hostable, model registry included. Alternative `wandb` requires account + internet. |
| UI | `gradio` | Fastest path from function to browser UI. Alternative `streamlit` is fine but Gradio has better image interaction (click events). |
| 3D visualization | `pyvista` | Production-quality VTK wrapper. Alternative `plotly` does not handle volumetric data well. |
| Testing | `pytest` | Standard. |
| Packaging | `pyproject.toml` (PEP 517) | Modern Python packaging standard. |
| CI | GitHub Actions | Free for public repos, integrates with PyPI release. |
| Container | Docker | Standard. Base image: `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime`. |

---

## 14. Implementation Phases

### Phase 1 — Data Foundation (Days 1–3)
- [ ] `geosam/io/segy.py` — load_volume, extract_time_slice, normalize_for_sam
- [ ] `geosam/attributes/` — all 5 attributes implemented and tested
- [ ] `geosam/attributes/pipeline.py` — compute_all returning dict
- [ ] Synthetic test fixture (50×50×200 SEG-Y)
- [ ] Unit tests for io/ and attributes/
- [ ] Notebook 01 and 02 with F3 dataset

**Completion check:** `pytest tests/test_io.py tests/test_attributes.py` passes. Notebook 02 renders all 5 attribute maps for F3.

### Phase 2 — SAM Integration (Days 4–8)
- [ ] `geosam/segmentation/sam_runner.py` — SeismicSAM class, segment_slice
- [ ] `geosam/segmentation/batch.py` — parallel multi-slice processing
- [ ] Logit normalization and attribute conversion
- [ ] Unit tests for sam_runner
- [ ] Notebook 03 — click a channel in F3, show mask + logit

**Completion check:** Can click on F3 time slice 150 and get a mask + logit that visually captures the channel.

### Phase 3 — SOM + MLflow (Days 9–12)
- [ ] `geosam/clustering/som.py` — SeismicSOM class
- [ ] `geosam/clustering/postprocess.py` — noise removal
- [ ] `geosam/tracking/mlflow_logger.py` — log params, metrics, artifacts
- [ ] Two-run experiment: attributes-only vs attributes+SAM-logits
- [ ] Notebook 04 — reproduce paper Figure 4 on F3

**Completion check:** MLflow UI shows two runs. Silhouette score is higher with SAM logits. Cluster map visually cleaner.

### Phase 4 — Gradio UI (Days 13–18)
- [ ] `app/gradio_app.py` — full interactive application
- [ ] Dockerfile for the app
- [ ] Dataset download helper scripts
- [ ] Notebook 05 — end-to-end pipeline tutorial

**Completion check:** `docker run geosam/app` launches in browser. Can load F3, click a channel, see SAM output, run SOM, export mask.

### Phase 5 — Release (Days 19–25)
- [ ] `pyproject.toml` with all dependencies
- [ ] GitHub Actions: CI on push, release to PyPI on tag
- [ ] README with screenshots, quickstart, dataset download instructions
- [ ] CONTRIBUTING.md
- [ ] `v0.1.0` tag + PyPI release
- [ ] Community posts (AAPG LinkedIn, SEG forum)

---

## 15. Success Metrics

### Technical quality
- All unit tests passing in CI
- Docker image builds in < 5 minutes
- Full F3 pipeline runs end-to-end without errors

### Research validity
- Silhouette score with SAM logits > silhouette score without SAM logits (reproduced from paper)
- MLflow experiment comparison shows measurable improvement
- Result visually comparable to paper Figure 4

### Community adoption (90-day targets)
- 50+ GitHub stars
- 100+ PyPI downloads
- At least 1 GitHub issue from an external user (proof someone is using it)
- Engagement from paper authors or AASPI Consortium members

### Career impact
- Listed on portfolio/CV as: "Lead author of open source geoscience AI toolkit — pip-installable, community adopted"
- Referenced in job interviews as proof of domain+ML+software engineering convergence

---

## 16. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SAM2 output quality poor on seismic data | Low | High | Paper validated it works. Start with F3 (well-studied). If quality is poor, try different SAM checkpoints or preprocessing. |
| SEG-Y header inconsistencies break I/O | Medium | Medium | Test against 3 different public datasets. Add explicit header parsing for each known dataset. Log warnings for non-standard headers. |
| GLCM too slow on full volume | Medium | Low | Compute per-slice with vectorized skimage. If still slow, downsample or use GPU texture computation via cupy. |
| SOM convergence poor | Low | Medium | Standard MiniSOM parameters are well-understood for seismic. If poor, increase iterations or try different grid sizes (log in MLflow). |
| No community adoption | Medium | Low (career impact only) | Reach out directly to paper authors on LinkedIn. Submit to awesome-geoscience-ml list. Write a clear LinkedIn post with a demo GIF. |

---

## 17. Out of Scope

The following are explicitly not part of GeoSAM v0.1.0:

- **Model training or fine-tuning** — that is Nexus. GeoSAM uses SAM2 as-is.
- **Fault interpretation** — different problem requiring different approaches (edge detection on vertical sections, not time slices).
- **Well log integration** — requires additional data types not addressable with SAM.
- **Depth conversion** — requires velocity models, a separate geophysical problem.
- **Petrel or Kingdom plugin** — requires proprietary SDK agreements.
- **Real-time streaming data** — acquisition processing is a different domain.
- **3D prompt propagation UI** — the Gradio UI handles single-slice prompting. Multi-slice propagation is scriptable via the Python API.
