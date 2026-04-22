"""
GeoSAM Visual Dashboard

Shows the full pipeline in one view:
  Input SEG-Y → seismic slice → attribute maps → SAM masks

Run from geosam project root (with venv active):
    python dashboard.py
Then open http://localhost:7860 in your browser.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
from pathlib import Path
import gradio as gr
import plotly.graph_objects as go

from geosam.io import load_volume, get_inline, get_crossline, get_timeslice, slice_to_rgb
from geosam.attributes import compute_all, ATTRIBUTE_NAMES
from geosam.sam import segment_auto, segment_with_points

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR  = Path("data")
CKPT_DIR  = Path("checkpoints")

DATASETS = {
    "synthetic_large.segy  (100×120×300 — fault, channel, bright spot)": DATA_DIR / "synthetic_large.segy",
    "f3.sgy                (23×18×75   — equinor test fixture)":          DATA_DIR / "f3.sgy",
}
CHECKPOINTS = {
    "sam2.1_hiera_tiny  (38M params — fast on CPU)": CKPT_DIR / "sam2.1_hiera_tiny.pt",
}
ATTR_CMAPS = {
    "envelope":  "plasma",
    "dip":       "hot",
    "coherence": "RdYlGn",
    "texture":   "viridis",
}
MASK_COLOURS = [
    "#FF3333", "#33FF57", "#3399FF",
    "#FFD700", "#FF33FF", "#00FFFF",
]


# ── Data cache (avoid reloading on every slider move) ─────────────────────────
_cache: dict = {}

def get_volume(dataset_label: str) -> np.ndarray:
    path = str(DATASETS[dataset_label])
    if path not in _cache:
        _cache[path] = load_volume(path)
    return _cache[path]


# ── 3D Volume Viewer ──────────────────────────────────────────────────────────
def render_3d(dataset_label: str, slice_type: str, slice_idx: int):
    vol = get_volume(dataset_label)
    n_il, n_xl, n_t = vol.shape

    max_idx = {"Inline": n_il - 1, "Crossline": n_xl - 1, "Timeslice": n_t - 1}[slice_type]
    slice_idx = int(np.clip(slice_idx, 0, max_idx))

    fig = go.Figure()

    # ── Cube wireframe ─────────────────────────────────────────────────────────
    il0, il1 = 0, n_il - 1
    xl0, xl1 = 0, n_xl - 1
    t0,  t1  = 0, n_t  - 1

    corners = dict(
        x=[il0, il1, il1, il0, il0, il1, il1, il0],
        y=[xl0, xl0, xl1, xl1, xl0, xl0, xl1, xl1],
        z=[t0,  t0,  t0,  t0,  t1,  t1,  t1,  t1],
    )
    edges = [(0,1),(1,2),(2,3),(3,0), (4,5),(5,6),(6,7),(7,4), (0,4),(1,5),(2,6),(3,7)]
    for a, b in edges:
        fig.add_trace(go.Scatter3d(
            x=[corners["x"][a], corners["x"][b]],
            y=[corners["y"][a], corners["y"][b]],
            z=[corners["z"][a], corners["z"][b]],
            mode="lines",
            line=dict(color="#666699", width=2),
            showlegend=False,
            hoverinfo="skip",
        ))

    # ── Current slice plane ────────────────────────────────────────────────────
    # Downsample heavy axes so plotly stays responsive
    def _ds(arr, max_pts=80):
        step = max(1, len(arr) // max_pts)
        return arr[::step]

    il_ax = _ds(np.arange(n_il))
    xl_ax = _ds(np.arange(n_xl))
    t_ax  = _ds(np.arange(n_t))

    def _norm(slc):
        lo, hi = np.percentile(slc, 2), np.percentile(slc, 98)
        return np.clip((slc - lo) / (hi - lo + 1e-9), 0, 1)

    if slice_type == "Inline":
        slc = vol[slice_idx, :, :]          # (n_xl, n_t)
        slc = slc[np.ix_(xl_ax, t_ax)]
        XL, T = np.meshgrid(xl_ax, t_ax, indexing="ij")
        IL = np.full_like(XL, slice_idx, dtype=float)
        label = f"Inline {slice_idx}"
        fig.add_trace(go.Surface(
            x=IL, y=XL, z=T, surfacecolor=_norm(slc),
            colorscale="RdBu", reversescale=True,
            showscale=False, opacity=1.0, name=label,
            hovertemplate="XL: %{y}<br>T: %{z}<extra>" + label + "</extra>",
        ))
        # Highlight line on cube face
        fig.add_trace(go.Scatter3d(
            x=[slice_idx]*4, y=[xl0,xl1,xl1,xl0], z=[t0,t0,t1,t1],
            mode="lines", line=dict(color="#FFD700", width=5),
            showlegend=False, hoverinfo="skip",
        ))

    elif slice_type == "Crossline":
        slc = vol[:, slice_idx, :]          # (n_il, n_t)
        slc = slc[np.ix_(il_ax, t_ax)]
        IL, T = np.meshgrid(il_ax, t_ax, indexing="ij")
        XL = np.full_like(IL, slice_idx, dtype=float)
        label = f"Crossline {slice_idx}"
        fig.add_trace(go.Surface(
            x=IL, y=XL, z=T, surfacecolor=_norm(slc),
            colorscale="RdBu", reversescale=True,
            showscale=False, opacity=1.0, name=label,
            hovertemplate="IL: %{x}<br>T: %{z}<extra>" + label + "</extra>",
        ))
        fig.add_trace(go.Scatter3d(
            x=[il0,il1,il1,il0], y=[slice_idx]*4, z=[t0,t0,t1,t1],
            mode="lines", line=dict(color="#FFD700", width=5),
            showlegend=False, hoverinfo="skip",
        ))

    else:  # Timeslice
        slc = vol[:, :, slice_idx]          # (n_il, n_xl)
        slc = slc[np.ix_(il_ax, xl_ax)]
        IL, XL = np.meshgrid(il_ax, xl_ax, indexing="ij")
        T = np.full_like(IL, slice_idx, dtype=float)
        label = f"Timeslice {slice_idx}"
        fig.add_trace(go.Surface(
            x=IL, y=XL, z=T, surfacecolor=_norm(slc),
            colorscale="RdBu", reversescale=True,
            showscale=False, opacity=1.0, name=label,
            hovertemplate="IL: %{x}<br>XL: %{y}<extra>" + label + "</extra>",
        ))
        fig.add_trace(go.Scatter3d(
            x=[il0,il1,il1,il0], y=[xl0,xl0,xl1,xl1], z=[slice_idx]*4,
            mode="lines", line=dict(color="#FFD700", width=5),
            showlegend=False, hoverinfo="skip",
        ))

    # ── Layout ─────────────────────────────────────────────────────────────────
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="#1a1a2e",
        font=dict(color="white", size=11),
        title=dict(
            text=f"3D Volume — {slice_type} <b>{slice_idx}</b> highlighted  |  "
                 f"{n_il} IL × {n_xl} XL × {n_t} T",
            font=dict(size=12, color="white"),
        ),
        scene=dict(
            bgcolor="#16213e",
            xaxis=dict(title="Inline",     gridcolor="#333", showbackground=True, backgroundcolor="#16213e"),
            yaxis=dict(title="Crossline",  gridcolor="#333", showbackground=True, backgroundcolor="#16213e"),
            zaxis=dict(title="Time sample (↓ = deeper)", gridcolor="#333",
                       showbackground=True, backgroundcolor="#16213e",
                       autorange="reversed"),
            camera=dict(eye=dict(x=1.6, y=1.6, z=1.2)),
            aspectmode="manual",
            aspectratio=dict(
                x=n_il / max(n_il, n_xl, n_t),
                y=n_xl / max(n_il, n_xl, n_t),
                z=n_t  / max(n_il, n_xl, n_t) * 1.5,
            ),
        ),
    )
    return fig


# ── Core render function ───────────────────────────────────────────────────────
def render(
    dataset_label: str,
    slice_type: str,
    slice_idx: int,
    ckpt_label: str,
    run_sam: bool,
    sam_mode: str,
    points_per_side: int,
    iou_thresh: float,
    stability_thresh: float,
    point_x: int,
    point_y: int,
):
    vol = get_volume(dataset_label)
    n_il, n_xl, n_t = vol.shape

    # Clamp index to valid range
    max_idx = {"Inline": n_il - 1, "Crossline": n_xl - 1, "Timeslice": n_t - 1}[slice_type]
    slice_idx = int(np.clip(slice_idx, 0, max_idx))

    # Extract slice
    if slice_type == "Inline":
        slc = get_inline(vol, slice_idx)
        xlabel, ylabel = "Crossline", "Time sample"
    elif slice_type == "Crossline":
        slc = get_crossline(vol, slice_idx)
        xlabel, ylabel = "Inline", "Time sample"
    else:
        slc = get_timeslice(vol, slice_idx)
        xlabel, ylabel = "Crossline", "Inline"

    rgb   = slice_to_rgb(slc)
    attrs = compute_all(slc)

    # ── Layout ────────────────────────────────────────────────────────────────
    #   Row 0: Raw amplitude  |  Envelope  |  Dip  |  Coherence  |  Texture
    #   Row 1: SAM on Raw RGB |  Mask 1   |  Mask 2  |  Mask 3   |  Mask 4
    n_cols = 5
    fig_h  = 10 if run_sam else 5
    fig, axes = plt.subplots(
        2 if run_sam else 1, n_cols,
        figsize=(n_cols * 3.5, fig_h),
        gridspec_kw={"hspace": 0.4, "wspace": 0.35},
    )
    if not run_sam:
        axes = axes[np.newaxis, :]   # make 2D for uniform indexing

    fig.patch.set_facecolor("#1a1a2e")
    for ax in axes.flat:
        ax.set_facecolor("#16213e")
        for sp in ax.spines.values():
            sp.set_color("#444")

    def style_ax(ax, title, cbar_img=None):
        ax.set_title(title, color="white", fontsize=9, pad=4)
        ax.set_xlabel(xlabel, color="#aaa", fontsize=7)
        ax.set_ylabel(ylabel, color="#aaa", fontsize=7)
        ax.tick_params(colors="#888", labelsize=6)

    # ── Row 0: inputs ─────────────────────────────────────────────────────────
    # Raw seismic
    ax = axes[0, 0]
    im = ax.imshow(slc, cmap="RdBu_r", aspect="auto",
                   vmin=np.percentile(slc, 2), vmax=np.percentile(slc, 98))
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02).ax.yaxis.set_tick_params(color="white", labelcolor="white")
    style_ax(ax, f"Raw amplitude  [{slice_type} {slice_idx}]\nred=+amp  blue=−amp")
    # Row label on left margin
    ax.set_ylabel("← INPUT\n" + ylabel, color="#88aaff", fontsize=7)

    # Attribute maps
    for col, name in enumerate(ATTRIBUTE_NAMES, start=1):
        ax  = axes[0, col]
        cmap = ATTR_CMAPS[name]
        ch  = attrs[..., ATTRIBUTE_NAMES.index(name)]
        im  = ax.imshow(ch, cmap=cmap, aspect="auto",
                        vmin=np.percentile(ch, 2), vmax=np.percentile(ch, 98))
        fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02).ax.yaxis.set_tick_params(color="white", labelcolor="white")
        style_ax(ax, name.capitalize())

    # ── Row 1: SAM ────────────────────────────────────────────────────────────
    if run_sam:
        ckpt = CHECKPOINTS[ckpt_label]
        masks_data = []
        error_msg  = None

        try:
            if sam_mode == "Automatic (find everything)":
                masks_data = segment_auto(
                    rgb, ckpt, device="cpu",
                    points_per_side=points_per_side,
                    pred_iou_thresh=iou_thresh,
                    stability_score_thresh=stability_thresh,
                )
            else:
                h, w = slc.shape
                px = int(np.clip(point_x, 0, w - 1))
                py = int(np.clip(point_y, 0, h - 1))
                mask = segment_with_points(
                    rgb, [(px, py)], checkpoint=ckpt, device="cpu"
                )
                masks_data = [{"segmentation": mask, "area": int(mask.sum()),
                               "predicted_iou": 1.0, "stability_score": 1.0}]
        except Exception as e:
            error_msg = str(e)

        # Overlay panel
        ax_overlay = axes[1, 0]
        ax_overlay.imshow(rgb, aspect="auto")

        legend_patches = []
        for i, m in enumerate(masks_data[:6]):
            colour = mcolors.to_rgba(MASK_COLOURS[i], alpha=0.45)
            overlay = np.zeros((*slc.shape, 4), dtype=np.float32)
            overlay[m["segmentation"]] = colour
            ax_overlay.imshow(overlay, aspect="auto")
            legend_patches.append(
                Patch(color=MASK_COLOURS[i],
                      label=f"M{i+1}  area={m['area']}  IoU={m['predicted_iou']:.2f}")
            )

        if sam_mode == "Point prompt" and not error_msg:
            h, w = slc.shape
            ax_overlay.plot(point_x, point_y, "y*", markersize=12, markeredgecolor="black")

        ax_overlay.legend(handles=legend_patches, loc="lower left",
                          fontsize=6, facecolor="#111", labelcolor="white",
                          framealpha=0.8)
        title_overlay = (
            f"SAM on Raw Amplitude → {len(masks_data)} masks\n"
            f"sorted largest→smallest  (SAM never saw attributes)"
            if not error_msg else f"SAM error:\n{error_msg[:60]}"
        )
        style_ax(ax_overlay, title_overlay)
        # Row label on left margin
        ax_overlay.set_ylabel("← SAM OUTPUT\n" + ylabel, color="#ffaa44", fontsize=7)

        # Individual mask panels (up to 4)
        for col in range(1, 5):
            ax = axes[1, col]
            if col - 1 < len(masks_data):
                m = masks_data[col - 1]
                cmap_mask = mcolors.LinearSegmentedColormap.from_list(
                    "mask", ["#16213e", MASK_COLOURS[col - 1]])
                ax.imshow(m["segmentation"].astype(float), cmap=cmap_mask, aspect="auto", vmin=0, vmax=1)
                style_ax(ax,
                    f"Mask {col}  (from raw amplitude)\n"
                    f"area={m['area']}px  IoU={m['predicted_iou']:.3f}\n"
                    f"stability={m['stability_score']:.3f}  "
                    f"| white=inside mask  black=outside"
                )
            else:
                ax.axis("off")
                ax.text(0.5, 0.5, f"Mask {col}\n(not found)", color="#555",
                        ha="center", va="center", transform=ax.transAxes, fontsize=9)

    # ── Title ─────────────────────────────────────────────────────────────────
    n_il, n_xl, n_t = vol.shape
    fig.suptitle(
        f"GeoSAM Pipeline  |  {Path(list(DATASETS.keys())[list(DATASETS.values()).index(DATASETS[dataset_label])]).stem}"
        f"  |  Volume: {n_il}IL × {n_xl}XL × {n_t}T",
        color="white", fontsize=11, y=1.01,
    )

    fig.tight_layout()
    return fig


# ── Gradio UI ─────────────────────────────────────────────────────────────────
def update_slice_max(dataset_label, slice_type):
    vol = get_volume(dataset_label)
    n_il, n_xl, n_t = vol.shape
    maxval = {"Inline": n_il - 1, "Crossline": n_xl - 1, "Timeslice": n_t - 1}[slice_type]
    return gr.update(maximum=maxval, value=min(50, maxval))


with gr.Blocks(title="GeoSAM Dashboard") as demo:

    gr.Markdown(
        "# GeoSAM Pipeline Dashboard\n"
        "**SEG-Y input → seismic slice → attribute maps → SAM segmentation masks**"
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Data")
            dataset_dd  = gr.Dropdown(list(DATASETS.keys()),  label="Dataset",    value=list(DATASETS.keys())[0])
            slice_type  = gr.Radio(["Inline", "Crossline", "Timeslice"],           label="Slice type", value="Inline")
            slice_idx   = gr.Slider(0, 99, value=50, step=1,                       label="Slice index")

        with gr.Column(scale=1):
            gr.Markdown("### SAM")
            run_sam     = gr.Checkbox(value=False,                                 label="Run SAM segmentation")
            ckpt_dd     = gr.Dropdown(list(CHECKPOINTS.keys()),                    label="Checkpoint", value=list(CHECKPOINTS.keys())[0])
            sam_mode    = gr.Radio(["Automatic (find everything)", "Point prompt"], label="Mode", value="Automatic (find everything)")

        with gr.Column(scale=1):
            gr.Markdown("### SAM Thresholds")
            pts_side    = gr.Slider(4, 32,  value=16, step=4,  label="Points per side (auto mode)")
            iou_thr     = gr.Slider(0.5, 0.99, value=0.70, step=0.05, label="IoU threshold")
            stab_thr    = gr.Slider(0.5, 0.99, value=0.80, step=0.05, label="Stability threshold")

        with gr.Column(scale=1):
            gr.Markdown("### Point Prompt (x, y)")
            pt_x = gr.Slider(0, 300, value=60,  step=1, label="Point X (column)")
            pt_y = gr.Slider(0, 120, value=50,  step=1, label="Point Y (row)")
            run_btn = gr.Button("▶  Run Pipeline", variant="primary", size="lg")

    # ── 3D Volume Viewer ──────────────────────────────────────────────────────
    with gr.Accordion("3D Volume — click to expand / collapse", open=True):
        gr.Markdown(
            "Drag to rotate · Scroll to zoom · **Gold outline** = current slice · "
            "Time axis is inverted (0 = surface, deeper = down)"
        )
        output_3d = gr.Plot(label="3D Volume View")

    output_plot = gr.Plot(label="Pipeline Visualisation")

    # Wire up slice index max when dataset or slice type changes
    dataset_dd.change(update_slice_max, [dataset_dd, slice_type], slice_idx)
    slice_type.change(update_slice_max, [dataset_dd, slice_type], slice_idx)

    # 3D view inputs (no SAM controls needed)
    view_3d_inputs = [dataset_dd, slice_type, slice_idx]

    # All inputs that should trigger a re-render
    all_inputs = [
        dataset_dd, slice_type, slice_idx, ckpt_dd,
        run_sam, sam_mode, pts_side, iou_thr, stab_thr, pt_x, pt_y,
    ]

    # 3D view updates on dataset/slice type change and on slider release
    dataset_dd.change(render_3d, inputs=view_3d_inputs, outputs=output_3d)
    slice_type.change(render_3d, inputs=view_3d_inputs, outputs=output_3d)
    slice_idx.release(render_3d, inputs=view_3d_inputs, outputs=output_3d)

    run_btn.click(render, inputs=all_inputs, outputs=output_plot)

    # Also re-render pipeline when slice index or type changes (no SAM, fast)
    slice_idx.release(render, inputs=all_inputs, outputs=output_plot)

    # ── Load both plots on page open ─────────────────────────────────────────
    demo.load(render_3d, inputs=view_3d_inputs, outputs=output_3d)
    demo.load(render,    inputs=all_inputs,     outputs=output_plot)


if __name__ == "__main__":
    print("Starting GeoSAM dashboard at http://localhost:7860")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        theme=gr.themes.Base(primary_hue="blue", neutral_hue="slate"),
    )
