"""VideoMobject for Manim Community."""

from .compat import ensure_pillow_compat
from .core import PlayVideo, VideoMobject

__all__ = ["VideoMobject", "PlayVideo", "ensure_pillow_compat"]
__version__ = "0.1.0"
