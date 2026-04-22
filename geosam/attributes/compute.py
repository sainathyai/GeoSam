"""
Seismic attribute computation for SAM input enhancement.

Each function takes a 2D amplitude slice (H, W) and returns a 2D
attribute array (H, W). All outputs are float32.

compute_all() stacks them into (H, W, N_attrs) — ready for ML pipelines.
"""

import numpy as np
from scipy.signal import hilbert
from scipy.ndimage import sobel, uniform_filter


def compute_envelope(slice_2d: np.ndarray) -> np.ndarray:
    """Instantaneous amplitude via Hilbert transform.

    Removes the seismic wavelet oscillation and returns the reflector
    strength envelope. Always positive; peaks sharply at geological
    boundaries regardless of polarity.

    Applied along the time axis (axis=1, columns).
    """
    analytic = hilbert(slice_2d.astype(np.float64), axis=1)
    return np.abs(analytic).astype(np.float32)


def compute_dip(slice_2d: np.ndarray) -> np.ndarray:
    """Structural dip magnitude via Sobel gradient.

    High values mark boundaries where amplitude changes rapidly
    (reflector edges, faults). Low values indicate laterally
    continuous, flat geology.
    """
    gx = sobel(slice_2d.astype(np.float64), axis=1)  # along time
    gy = sobel(slice_2d.astype(np.float64), axis=0)  # along space
    return np.sqrt(gx ** 2 + gy ** 2).astype(np.float32)


def compute_coherence(slice_2d: np.ndarray, window: int = 5) -> np.ndarray:
    """Local semblance: similarity of each trace to its neighbours.

    Computed as 1 - (local variance / local mean power). Values near 1
    mean adjacent traces look alike (layered geology). Values near 0
    mean divergence (faults, channels, noise).

    Parameters
    ----------
    window : int
        Side length of the local neighbourhood in samples. Default 5.
    """
    s = slice_2d.astype(np.float64)
    local_mean_sq = uniform_filter(s, size=window) ** 2
    local_sq_mean = uniform_filter(s ** 2, size=window)
    numerator   = local_mean_sq
    denominator = local_sq_mean + 1e-10  # avoid divide-by-zero
    coherence = (numerator / denominator).astype(np.float32)
    return np.clip(coherence, 0.0, 1.0)


def compute_texture(slice_2d: np.ndarray, window: int = 5) -> np.ndarray:
    """Local amplitude roughness via windowed standard deviation.

    High values = chaotic reflectors (gas sands, mass transport).
    Low values  = smooth, homogeneous facies (shale, evaporite).

    Parameters
    ----------
    window : int
        Side length of the local neighbourhood in samples. Default 5.
    """
    s = slice_2d.astype(np.float64)
    local_mean   = uniform_filter(s, size=window)
    local_sq     = uniform_filter(s ** 2, size=window)
    variance     = local_sq - local_mean ** 2
    return np.sqrt(np.maximum(variance, 0)).astype(np.float32)


# Ordered list of (name, function) pairs — defines axis order in the stack
_ATTRIBUTES = [
    ("envelope",  compute_envelope),
    ("dip",       compute_dip),
    ("coherence", compute_coherence),
    ("texture",   compute_texture),
]

ATTRIBUTE_NAMES = [name for name, _ in _ATTRIBUTES]


def compute_all(slice_2d: np.ndarray, window: int = 5) -> np.ndarray:
    """Compute all seismic attributes and return a stacked array.

    Parameters
    ----------
    slice_2d : np.ndarray
        2D amplitude slice, shape (H, W). Any float dtype.
    window : int
        Neighbourhood window for coherence and texture. Default 5.

    Returns
    -------
    np.ndarray
        Shape (H, W, 4), dtype float32.
        Axis 2 order: envelope, dip, coherence, texture.
        Access by name via ATTRIBUTE_NAMES.

    Examples
    --------
    >>> attrs = compute_all(timeslice)
    >>> attrs.shape
    (23, 18, 4)
    >>> envelope = attrs[..., ATTRIBUTE_NAMES.index("envelope")]
    """
    h, w = slice_2d.shape
    out = np.empty((h, w, len(_ATTRIBUTES)), dtype=np.float32)
    for i, (name, fn) in enumerate(_ATTRIBUTES):
        kwargs = {"window": window} if name in ("coherence", "texture") else {}
        out[..., i] = fn(slice_2d, **kwargs)
    return out
