"""SEG-Y file I/O for seismic volumes."""

import numpy as np
from pathlib import Path


def load_volume(path: str | Path) -> np.ndarray:
    """Load a SEG-Y file into a 3D numpy array (inlines, crosslines, samples).

    Parameters
    ----------
    path : str | Path
        Path to the .segy or .sgy file.

    Returns
    -------
    np.ndarray
        Shape: (n_inlines, n_crosslines, n_samples). dtype float32.

    Examples
    --------
    >>> volume = load_volume("f3.segy")
    >>> volume.shape
    (651, 951, 462)
    """
    try:
        import os, sys
        if sys.platform == "win32":
            # On Windows, segyio's C extension needs MSVC runtime DLLs.
            # Python 3.8+ restricts DLL search paths; add segyio's package
            # directory so VCRUNTIME140.dll etc. are found if placed there.
            import importlib.util
            segyio_dir = os.path.dirname(importlib.util.find_spec("segyio").origin)
            os.add_dll_directory(segyio_dir)
        import segyio
    except ImportError:
        raise ImportError("segyio is required: pip install segyio")

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"SEG-Y file not found: {path}")

    try:
        with segyio.open(str(path), iline=189, xline=193, ignore_geometry=False) as f:
            return segyio.tools.cube(f).astype(np.float32)
    except ValueError:
        pass

    # Fallback for files with irregular geometry (e.g. F3 which has 434 extra traces).
    # Read all traces, map inline/crossline headers to grid indices, fill a zero-padded cube.
    with segyio.open(str(path), iline=189, xline=193, ignore_geometry=True) as f:
        ilines    = f.attributes(segyio.TraceField.INLINE_3D)[:]
        xlines    = f.attributes(segyio.TraceField.CROSSLINE_3D)[:]
        n_samples = len(f.samples)
        all_traces = f.trace.raw[:].astype(np.float32)  # (n_traces, n_samples)

    il_sorted = np.sort(np.unique(ilines))
    xl_sorted = np.sort(np.unique(xlines))
    il_map = {int(v): i for i, v in enumerate(il_sorted)}
    xl_map = {int(v): i for i, v in enumerate(xl_sorted)}

    volume = np.zeros((len(il_sorted), len(xl_sorted), n_samples), dtype=np.float32)
    il_idx = np.array([il_map[int(v)] for v in ilines])
    xl_idx = np.array([xl_map[int(v)] for v in xlines])
    volume[il_idx, xl_idx, :] = all_traces

    return volume


def get_inline(volume: np.ndarray, index: int) -> np.ndarray:
    """Extract a single inline slice. Shape: (crosslines, samples)."""
    return volume[index, :, :]


def get_crossline(volume: np.ndarray, index: int) -> np.ndarray:
    """Extract a single crossline slice. Shape: (inlines, samples)."""
    return volume[:, index, :]


def get_timeslice(volume: np.ndarray, index: int) -> np.ndarray:
    """Extract a horizontal time slice. Shape: (inlines, crosslines)."""
    return volume[:, :, index]


def normalize_slice(slice_2d: np.ndarray) -> np.ndarray:
    """Normalize a 2D slice to [0, 1] range for visualization/SAM input."""
    min_val, max_val = slice_2d.min(), slice_2d.max()
    if max_val == min_val:
        return np.zeros_like(slice_2d, dtype=np.float32)
    return ((slice_2d - min_val) / (max_val - min_val)).astype(np.float32)


def slice_to_rgb(slice_2d: np.ndarray) -> np.ndarray:
    """Convert a normalized 2D slice to an RGB image array for SAM.

    SAM expects uint8 RGB input of shape (H, W, 3).
    We replicate the grayscale slice across all 3 channels.

    Parameters
    ----------
    slice_2d : np.ndarray
        2D float array, values in any range.

    Returns
    -------
    np.ndarray
        Shape (H, W, 3), dtype uint8, values 0-255.
    """
    normalized = normalize_slice(slice_2d)
    gray_uint8 = (normalized * 255).astype(np.uint8)
    return np.stack([gray_uint8, gray_uint8, gray_uint8], axis=-1)
