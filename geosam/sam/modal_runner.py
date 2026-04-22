"""
Modal.com GPU runner for SAM2 inference.

Usage:
  # One-time: download checkpoints into the Modal volume
  modal run geosam/sam/modal_runner.py::download_checkpoints

  # Deploy the app so FastAPI can call it
  modal deploy geosam/sam/modal_runner.py

  # Then start FastAPI with Modal enabled
  GEOSAM_USE_MODAL=1 uvicorn api.main:app --reload --port 8000
"""

import modal

app = modal.App("geosam-sam")

# Persistent volume — checkpoints download once, reused across all container restarts
volume = modal.Volume.from_name("geosam-checkpoints", create_if_missing=True)

CHECKPOINT_DIR = "/checkpoints"

CHECKPOINT_URLS = {
    "tiny":      "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt",
    "small":     "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_small.pt",
    "base_plus": "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt",
    "large":     "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt",
}

# Container image — built once, cached by Modal.
# Uses the official PyTorch CUDA image so torch+CUDA are pre-installed.
# SAM2 is installed directly from Meta's GitHub repo (not on PyPI).
image = (
    modal.Image.from_registry("pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime")
    .apt_install("git")
    .pip_install("numpy>=1.24", "Pillow>=9.5")
    .run_commands("pip install git+https://github.com/facebookresearch/sam2.git")
)


# ── One-time setup ─────────────────────────────────────────────────────────────

@app.function(volumes={CHECKPOINT_DIR: volume}, timeout=600, image=image)
def download_checkpoints():
    """Download all SAM2.1 checkpoints into the Modal volume.

    Run once before first inference:
        modal run geosam/sam/modal_runner.py::download_checkpoints
    """
    import urllib.request
    from pathlib import Path

    for size in CHECKPOINT_URLS:
        url  = CHECKPOINT_URLS[size]
        dest = Path(CHECKPOINT_DIR) / f"sam2.1_hiera_{size}.pt"
        if dest.exists():
            print(f"  {size}: already cached ({dest.stat().st_size / 1e6:.0f} MB)")
            continue
        print(f"  {size}: downloading {url} ...")
        urllib.request.urlretrieve(url, str(dest))
        print(f"  {size}: done ({dest.stat().st_size / 1e6:.0f} MB)")
    volume.commit()
    print("All checkpoints ready.")


# ── GPU inference — class-based so the model is loaded once per container ─────

CFG_MAP = {
    "tiny":      "configs/sam2.1/sam2.1_hiera_t.yaml",
    "small":     "configs/sam2.1/sam2.1_hiera_s.yaml",
    "base_plus": "configs/sam2.1/sam2.1_hiera_b+.yaml",
    "large":     "configs/sam2.1/sam2.1_hiera_l.yaml",
}


@app.cls(
    gpu="A10G",
    image=image,
    volumes={CHECKPOINT_DIR: volume},
    timeout=120,
    max_containers=5,
)
class SAMRunner:
    """Stateful Modal class — model weights are loaded once on container start
    and reused for every subsequent request on the same warm container.
    """

    model_size: str = modal.parameter(default="tiny")

    @modal.enter()
    def load_model(self):
        """Runs once when the container starts. Loads model weights into GPU VRAM."""
        import torch
        from pathlib import Path
        from sam2.build_sam import build_sam2

        ckpt = Path(CHECKPOINT_DIR) / f"sam2.1_hiera_{self.model_size}.pt"
        self._model = build_sam2(CFG_MAP[self.model_size], str(ckpt), device="cuda")
        self._torch = torch
        print(f"[SAMRunner] Loaded {self.model_size} model on GPU.")

    @modal.method()
    def run(
        self,
        rgb_bytes: bytes,
        image_shape: tuple[int, int],
        points_per_side: int = 16,
        iou_thresh: float = 0.70,
        stability_thresh: float = 0.80,
    ) -> dict:
        """Run automatic mask generation. Model is already loaded — fast path only.

        Returns dict with 'overlay_b64' and 'masks' list (same schema as /sam endpoint).
        """
        import io
        import base64
        import numpy as np
        from PIL import Image
        from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator

        H, W = image_shape
        rgb = np.frombuffer(rgb_bytes, dtype=np.uint8).reshape(H, W, 3)

        generator = SAM2AutomaticMaskGenerator(
            self._model,
            points_per_side=points_per_side,
            pred_iou_thresh=iou_thresh,
            stability_score_thresh=stability_thresh,
        )

        with self._torch.inference_mode():
            raw_masks = generator.generate(rgb)

        raw_masks.sort(key=lambda m: m["area"], reverse=True)

        def _mask_b64(seg):
            img = Image.fromarray((seg * 255).astype(np.uint8), mode="L")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()

        def _overlay_b64(rgb_arr, masks):
            COLOURS = [(255,51,51),(51,255,87),(51,153,255),(255,215,0),(255,51,255),(0,255,255)]
            base = rgb_arr.copy().astype(np.float32)
            for i, m in enumerate(masks[:6]):
                c = COLOURS[i % len(COLOURS)]
                seg = m["segmentation"]
                for ch, v in enumerate(c):
                    base[:,:,ch] = np.where(seg, base[:,:,ch]*0.55 + v*0.45, base[:,:,ch])
            img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()

        return {
            "overlay_b64": _overlay_b64(rgb, raw_masks),
            "masks": [
                {
                    "mask_b64":        _mask_b64(m["segmentation"]),
                    "area":            int(m["area"]),
                    "predicted_iou":   round(float(m["predicted_iou"]), 4),
                    "stability_score": round(float(m["stability_score"]), 4),
                }
                for m in raw_masks
            ],
        }


# Module-level convenience function — called by api/main.py via .remote()
def run_sam_gpu(
    rgb_bytes: bytes,
    image_shape: tuple[int, int],
    model_size: str = "tiny",
    points_per_side: int = 16,
    iou_thresh: float = 0.70,
    stability_thresh: float = 0.80,
) -> dict:
    """Dispatch to the correct SAMRunner instance for the given model_size."""
    runner = SAMRunner(model_size=model_size)
    return runner.run.remote(rgb_bytes, image_shape, points_per_side, iou_thresh, stability_thresh)
