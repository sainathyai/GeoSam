"""
GeoSAM FastAPI backend

Endpoints:
  GET  /datasets                   → available datasets
  GET  /slice                      → 5 attribute images as base64 PNG
  POST /sam                        → run SAM on one attribute input, return all masks
  POST /sam/all                    → run SAM on all 5 inputs, return per-input mask lists

Run from geosam project root (venv active):
    uvicorn api.main:app --reload --port 8000
"""

import io
import json
import os
import base64
from pathlib import Path
from typing import Literal

import numpy as np
import matplotlib
import plotly.graph_objects as go
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from geosam.io import load_volume, get_inline, get_crossline, get_timeslice, slice_to_rgb
from geosam.attributes import compute_all, ATTRIBUTE_NAMES
from geosam.sam import segment_auto, segment_with_points

# Set GEOSAM_USE_MODAL=1 to dispatch SAM inference to Modal GPU instead of local CPU
USE_MODAL = os.getenv("GEOSAM_USE_MODAL", "0") == "1"
if USE_MODAL:
    from geosam.sam.modal_runner import run_sam_gpu

# When running in Cloud Run, datasets and checkpoints are pulled from GCS on first
# access and cached locally at /tmp. Set GEOSAM_GCS_BUCKET to enable this path.
GCS_BUCKET = os.getenv("GEOSAM_GCS_BUCKET", "")
GCS_CKPT_BUCKET = os.getenv("GEOSAM_GCS_CKPT_BUCKET", "")

def _gcs_local(bucket: str, blob: str, local_dir: str) -> Path:
    """Download blob from GCS to local_dir if not already cached, return local path."""
    local = Path(local_dir) / blob
    if not local.exists():
        local.parent.mkdir(parents=True, exist_ok=True)
        from google.cloud import storage as gcs
        client = gcs.Client()
        client.bucket(bucket).blob(blob).download_to_filename(str(local))
    return local

app = FastAPI(title="GeoSAM API", version="0.1.0")

# Allow production domain + local dev
_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://geosam.veritasintelai.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path(os.getenv("GEOSAM_DATA_DIR", "data"))
CKPT_DIR = Path(os.getenv("GEOSAM_CKPT_DIR", "checkpoints"))

DATASETS = {
    "synthetic_large": DATA_DIR / "synthetic_large.segy",
    "f3":              DATA_DIR / "f3.sgy",
}

CHECKPOINTS = {
    "tiny":      CKPT_DIR / "sam2.1_hiera_tiny.pt",
    "small":     CKPT_DIR / "sam2.1_hiera_small.pt",
    "base_plus": CKPT_DIR / "sam2.1_hiera_base_plus.pt",
    "large":     CKPT_DIR / "sam2.1_hiera_large.pt",
}

ATTR_CMAPS = {
    "raw":        "RdBu_r",
    "envelope":   "plasma",
    "dip":        "hot",
    "coherence":  "RdYlGn",
    "texture":    "viridis",
}

SAM_INPUT_LABELS = ["raw", "envelope", "dip", "coherence", "texture"]

# ── Cache ─────────────────────────────────────────────────────────────────────
_vol_cache: dict = {}

def get_volume(name: str) -> np.ndarray:
    if name not in DATASETS:
        raise HTTPException(404, f"Dataset '{name}' not found")
    path = DATASETS[name]
    if GCS_BUCKET and not path.exists():
        path = _gcs_local(GCS_BUCKET, path.name, "/tmp/geosam/data")
    key = str(path)
    if key not in _vol_cache:
        _vol_cache[key] = load_volume(str(path))
    return _vol_cache[key]


# ── Image helpers ─────────────────────────────────────────────────────────────
def array_to_b64(arr: np.ndarray, cmap: str) -> str:
    """Float32 2D array → base64 PNG using given colormap."""
    lo, hi = np.percentile(arr, 2), np.percentile(arr, 98)
    norm = np.clip((arr - lo) / (hi - lo + 1e-9), 0, 1)
    colormap = plt.get_cmap(cmap)
    rgb = (colormap(norm)[:, :, :3] * 255).astype(np.uint8)
    img = Image.fromarray(rgb)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def mask_to_b64(mask: np.ndarray) -> str:
    """Boolean 2D mask → base64 grayscale PNG (white=inside, black=outside)."""
    img = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def overlay_to_b64(rgb: np.ndarray, masks: list[dict]) -> str:
    """Raw RGB image with all masks painted as semi-transparent overlays → base64 PNG."""
    COLOURS = [
        (255, 51,  51),   # red
        (51,  255, 87),   # green
        (51,  153, 255),  # blue
        (255, 215, 0),    # gold
        (255, 51,  255),  # magenta
        (0,   255, 255),  # cyan
    ]
    base = rgb.copy().astype(np.float32)
    for i, m in enumerate(masks[:6]):
        colour = COLOURS[i % len(COLOURS)]
        seg = m["segmentation"]
        for c, v in enumerate(colour):
            base[:, :, c] = np.where(seg, base[:, :, c] * 0.55 + v * 0.45, base[:, :, c])
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def get_sam_input(slc: np.ndarray, attrs: np.ndarray, input_name: str) -> np.ndarray:
    """Return the RGB uint8 image SAM should receive for the given input type."""
    if input_name == "raw":
        return slice_to_rgb(slc)
    idx = ATTRIBUTE_NAMES.index(input_name)   # envelope=0, dip=1, coherence=2, texture=3
    attr_slice = attrs[..., idx]
    return array_to_rgb_uint8(attr_slice, ATTR_CMAPS[input_name])


def array_to_rgb_uint8(arr: np.ndarray, cmap: str) -> np.ndarray:
    """Float32 2D array → (H, W, 3) uint8 for SAM input."""
    lo, hi = np.percentile(arr, 2), np.percentile(arr, 98)
    norm = np.clip((arr - lo) / (hi - lo + 1e-9), 0, 1)
    colormap = plt.get_cmap(cmap)
    return (colormap(norm)[:, :, :3] * 255).astype(np.uint8)


# ── Request / Response models ──────────────────────────────────────────────────
class SliceRequest(BaseModel):
    dataset:    str = "synthetic_large"
    slice_type: Literal["inline", "crossline", "timeslice"] = "inline"
    slice_idx:  int = 50


class SAMRequest(BaseModel):
    dataset:          str = "synthetic_large"
    slice_type:       Literal["inline", "crossline", "timeslice"] = "inline"
    slice_idx:        int = 50
    sam_input:        Literal["raw", "envelope", "dip", "coherence", "texture"] = "raw"
    model_size:       Literal["tiny", "small", "base_plus", "large"] = "tiny"
    points_per_side:  int = 16
    iou_thresh:       float = 0.70
    stability_thresh: float = 0.80


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/datasets")
def list_datasets():
    result = []
    for name, path in DATASETS.items():
        if path.exists():
            vol = get_volume(name)
            n_il, n_xl, n_t = vol.shape
            result.append({
                "id":    name,
                "label": f"{name}  ({n_il}×{n_xl}×{n_t})",
                "shape": {"inlines": n_il, "crosslines": n_xl, "time_samples": n_t},
            })
    return result


@app.post("/slice")
def get_slice(req: SliceRequest):
    """Return all 5 attribute images for the requested slice as base64 PNGs."""
    vol = get_volume(req.dataset)
    n_il, n_xl, n_t = vol.shape

    max_idx = {"inline": n_il - 1, "crossline": n_xl - 1, "timeslice": n_t - 1}[req.slice_type]
    idx = int(np.clip(req.slice_idx, 0, max_idx))

    if req.slice_type == "inline":
        slc = get_inline(vol, idx)
    elif req.slice_type == "crossline":
        slc = get_crossline(vol, idx)
    else:
        slc = get_timeslice(vol, idx)

    attrs = compute_all(slc)

    images = {"raw": array_to_b64(slc, "RdBu_r")}
    for i, name in enumerate(ATTRIBUTE_NAMES):    # envelope, dip, coherence, texture
        images[name] = array_to_b64(attrs[..., i], ATTR_CMAPS[name])

    return {
        "slice_type": req.slice_type,
        "slice_idx":  idx,
        "shape":      {"height": slc.shape[0], "width": slc.shape[1]},
        "images":     images,
    }


@app.post("/sam")
def run_sam(req: SAMRequest):
    """Run SAM on one attribute input. Returns overlay + all individual masks.

    Dispatches to Modal GPU when GEOSAM_USE_MODAL=1, otherwise runs on local CPU.
    """
    vol = get_volume(req.dataset)
    n_il, n_xl, n_t = vol.shape

    max_idx = {"inline": n_il - 1, "crossline": n_xl - 1, "timeslice": n_t - 1}[req.slice_type]
    idx = int(np.clip(req.slice_idx, 0, max_idx))

    if req.slice_type == "inline":
        slc = get_inline(vol, idx)
    elif req.slice_type == "crossline":
        slc = get_crossline(vol, idx)
    else:
        slc = get_timeslice(vol, idx)

    attrs     = compute_all(slc)
    rgb_input = get_sam_input(slc, attrs, req.sam_input)

    if USE_MODAL:
        # Dispatch to Modal GPU — run_sam_gpu handles .remote() internally
        result = run_sam_gpu(
            rgb_input.tobytes(),
            rgb_input.shape[:2],
            req.model_size,
            req.points_per_side,
            req.iou_thresh,
            req.stability_thresh,
        )
        return {
            "sam_input":   req.sam_input,
            "mask_count":  len(result["masks"]),
            "overlay_b64": result["overlay_b64"],
            "masks":       result["masks"],
        }

    # CPU fallback — uses local checkpoint
    ckpt = CHECKPOINTS.get(req.model_size)
    if not ckpt or not ckpt.exists():
        raise HTTPException(404, f"Checkpoint '{req.model_size}' not found at {ckpt}. "
                                 "Download it or set GEOSAM_USE_MODAL=1.")

    masks_raw   = segment_auto(
        rgb_input, ckpt, device="cpu",
        points_per_side=req.points_per_side,
        pred_iou_thresh=req.iou_thresh,
        stability_score_thresh=req.stability_thresh,
    )
    overlay_b64 = overlay_to_b64(rgb_input, masks_raw)
    masks_out   = [
        {
            "mask_b64":        mask_to_b64(m["segmentation"]),
            "area":            int(m["area"]),
            "predicted_iou":   round(float(m["predicted_iou"]), 4),
            "stability_score": round(float(m["stability_score"]), 4),
        }
        for m in masks_raw
    ]

    return {
        "sam_input":   req.sam_input,
        "mask_count":  len(masks_out),
        "overlay_b64": overlay_b64,
        "masks":       masks_out,
    }


@app.post("/sam/all")
def run_sam_all(req: SAMRequest):
    """Run SAM on all 5 inputs sequentially. Returns one result block per input."""
    results = {}
    for input_name in SAM_INPUT_LABELS:
        sub_req = req.model_copy(update={"sam_input": input_name})
        results[input_name] = run_sam(sub_req)
    return results


@app.get("/plot3d")
def get_plot3d(
    dataset:    str = "synthetic_large",
    slice_type: str = "inline",
    slice_idx:  int = 50,
):
    """Return a Plotly 3D seismic cube figure as JSON (for react-plotly.js)."""
    vol     = get_volume(dataset)
    n_il, n_xl, n_t = vol.shape
    max_idx = {"inline": n_il-1, "crossline": n_xl-1, "timeslice": n_t-1}[slice_type]
    idx     = int(np.clip(slice_idx, 0, max_idx))

    fig = go.Figure()

    # Wireframe cube edges
    il0, il1 = 0, n_il - 1
    xl0, xl1 = 0, n_xl - 1
    t0,  t1  = 0, n_t  - 1
    corners  = dict(x=[il0,il1,il1,il0,il0,il1,il1,il0],
                    y=[xl0,xl0,xl1,xl1,xl0,xl0,xl1,xl1],
                    z=[t0, t0, t0, t0, t1, t1, t1, t1])
    edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    for a, b in edges:
        fig.add_trace(go.Scatter3d(
            x=[corners["x"][a], corners["x"][b]],
            y=[corners["y"][a], corners["y"][b]],
            z=[corners["z"][a], corners["z"][b]],
            mode="lines", line=dict(color="#4a5580", width=2),
            showlegend=False, hoverinfo="skip",
        ))

    # Downsampled slice surface
    def _ds(arr, mx=60):
        step = max(1, len(arr) // mx); return arr[::step]
    def _norm(s):
        lo, hi = np.percentile(s, 2), np.percentile(s, 98)
        return np.clip((s - lo) / (hi - lo + 1e-9), 0, 1)

    il_ax = _ds(np.arange(n_il))
    xl_ax = _ds(np.arange(n_xl))
    t_ax  = _ds(np.arange(n_t))

    if slice_type == "inline":
        slc = vol[idx, :, :][np.ix_(xl_ax, t_ax)]
        XL, T = np.meshgrid(xl_ax, t_ax, indexing="ij")
        IL = np.full_like(XL, idx, dtype=float)
        fig.add_trace(go.Surface(x=IL, y=XL, z=T, surfacecolor=_norm(slc),
            colorscale="RdBu", reversescale=True, showscale=False, opacity=0.95))
        fig.add_trace(go.Scatter3d(
            x=[idx]*4, y=[xl0,xl1,xl1,xl0], z=[t0,t0,t1,t1],
            mode="lines", line=dict(color="#f59e0b", width=4),
            showlegend=False, hoverinfo="skip"))
    elif slice_type == "crossline":
        slc = vol[:, idx, :][np.ix_(il_ax, t_ax)]
        IL, T = np.meshgrid(il_ax, t_ax, indexing="ij")
        XL = np.full_like(IL, idx, dtype=float)
        fig.add_trace(go.Surface(x=IL, y=XL, z=T, surfacecolor=_norm(slc),
            colorscale="RdBu", reversescale=True, showscale=False, opacity=0.95))
        fig.add_trace(go.Scatter3d(
            x=[il0,il1,il1,il0], y=[idx]*4, z=[t0,t0,t1,t1],
            mode="lines", line=dict(color="#f59e0b", width=4),
            showlegend=False, hoverinfo="skip"))
    else:
        slc = vol[:, :, idx][np.ix_(il_ax, xl_ax)]
        IL, XL = np.meshgrid(il_ax, xl_ax, indexing="ij")
        T = np.full_like(IL, idx, dtype=float)
        fig.add_trace(go.Surface(x=IL, y=XL, z=T, surfacecolor=_norm(slc),
            colorscale="RdBu", reversescale=True, showscale=False, opacity=0.95))
        fig.add_trace(go.Scatter3d(
            x=[il0,il1,il1,il0], y=[xl0,xl0,xl1,xl1], z=[idx]*4,
            mode="lines", line=dict(color="#f59e0b", width=4),
            showlegend=False, hoverinfo="skip"))

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#060d1a",
        scene=dict(
            bgcolor="#060d1a",
            xaxis=dict(title="Inline",    gridcolor="#1e2a3a", showbackground=True, backgroundcolor="#060d1a"),
            yaxis=dict(title="Crossline", gridcolor="#1e2a3a", showbackground=True, backgroundcolor="#060d1a"),
            zaxis=dict(title="Time ↓",    gridcolor="#1e2a3a", showbackground=True, backgroundcolor="#060d1a", autorange="reversed"),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.1)),
            aspectmode="manual",
            aspectratio=dict(
                x=n_il/max(n_il,n_xl,n_t),
                y=n_xl/max(n_il,n_xl,n_t),
                z=n_t /max(n_il,n_xl,n_t)*1.4,
            ),
        ),
        font=dict(color="#94a3b8", size=10),
    )

    return json.loads(fig.to_json())
