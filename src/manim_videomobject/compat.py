"""Small compatibility helpers for Manim + Pillow versions."""

from __future__ import annotations

import numpy as np
from PIL import Image


def ensure_pillow_compat() -> None:
    """Work around Pillow >= 11 rejecting Manim's 2-D RGBA canvas.

    ``manim.camera.camera.Camera.display_image_mobject`` builds its paste canvas
    with ``np.zeros((h, w))`` (float64) and passes ``mode="RGBA"``. Newer Pillow
    raises ``ValueError: Invalid mode for data type``. The patch only rewrites
    that exact call shape (2-D array + RGBA) and leaves every other call alone.
    """
    if getattr(Image, "_mvo_pillow_patch", False):
        return

    original = Image.fromarray

    def fromarray(obj, mode=None):
        if mode == "RGBA" and getattr(obj, "ndim", 0) == 2:
            obj = np.zeros(obj.shape + (4,), dtype=np.uint8)
            mode = None
        return original(obj, mode)

    Image.fromarray = fromarray
    Image._mvo_pillow_patch = True
