"""VideoMobject for Manim Community: play short MP4 clips as frame sequences."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from manim import Animation, ImageMobject, linear

from .compat import ensure_pillow_compat

__all__ = ["VideoMobject", "PlayVideo"]


def _fraction(value: str, default: float = 30.0) -> float:
    """Parse ffprobe's ``30000/1001`` style frame rate."""
    if not value:
        return default
    try:
        num, _, den = value.partition("/")
        den = den or "1"
        rate = float(num) / float(den)
        return rate if rate > 0 else default
    except (ValueError, ZeroDivisionError):
        return default


def _probe(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration:format=duration",
        "-of", "json", str(path),
    ]
    try:
        raw = subprocess.check_output(cmd, text=True)
    except FileNotFoundError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("ffprobe is required; install ffmpeg") from exc
    data = json.loads(raw)
    stream = data["streams"][0]
    duration = stream.get("duration") or data.get("format", {}).get("duration")
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": _fraction(stream.get("r_frame_rate", "")),
        "duration": float(duration or 0.0),
    }


def _even(value: int) -> int:
    return max(2, value - value % 2)


class VideoMobject(ImageMobject):
    """An :class:`~manim.mobject.types.image_mobject.ImageMobject` backed by a video.

    Frames are extracted once with ffmpeg into a temporary JPEG sequence, then
    loaded lazily and cached. The mobject itself is always the current frame, so
    it composes with Manim's normal transforms, fades and camera.

    Parameters
    ----------
    file_path
        MP4/MOV/WebM file. Audio is ignored.
    fps
        Playback frame rate. Defaults to the source rate.
    start, end
        Clip window in seconds. ``end=None`` means the source duration.
    loop
        Wrap around when ``duration`` is exceeded.
    width, height, max_width
        Output frame size. ``max_width`` scales down only.
    cache_dir
        Keep extracted frames here instead of a temporary directory.
    max_cache
        Number of decoded frames kept in memory (LRU).
    patch_pillow
        Apply the Pillow 12 RGBA compatibility patch used by Manim <= 0.22.

    Examples
    --------
    .. code-block:: python

        clip = VideoMobject("take.mp4", start=2, end=8).scale_to_fit_width(8)
        self.add(clip)
        self.play(clip.play())
    """

    def __init__(
        self,
        file_path: str | Path,
        *,
        fps: float | None = None,
        start: float = 0.0,
        end: float | None = None,
        loop: bool = False,
        width: int | None = None,
        height: int | None = None,
        max_width: int | None = None,
        cache_dir: str | Path | None = None,
        max_cache: int = 48,
        patch_pillow: bool = True,
        **kwargs,
    ) -> None:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        if patch_pillow:
            ensure_pillow_compat()

        info = _probe(path)
        src_fps = info["fps"] or 30.0
        self.fps = float(fps or src_fps)
        self.loop = bool(loop)
        self.source_fps = src_fps
        self.source_duration = info["duration"]

        start = max(0.0, float(start))
        if end is None:
            end = self.source_duration
        end = min(float(end), self.source_duration) if self.source_duration else float(end)
        if end <= start:
            raise ValueError(f"empty clip window: start={start}, end={end}")
        self.start = start
        self.end = end

        out_w, out_h = self._target_size(info["width"], info["height"], width, height, max_width)
        self.frame_width_px = out_w
        self.frame_height_px = out_h

        if cache_dir is None:
            self._tmpdir = Path(tempfile.mkdtemp(prefix="manim-video-"))
            self._owns_dir = True
        else:
            self._tmpdir = Path(cache_dir).expanduser().resolve()
            self._tmpdir.mkdir(parents=True, exist_ok=True)
            self._owns_dir = False

        self._extract(path, out_w, out_h)
        self._files = sorted(self._tmpdir.glob("*.jpg"))
        if not self._files:
            self.close()
            raise RuntimeError(f"ffmpeg produced no frames for {path}")
        self.duration = len(self._files) / self.fps
        self._cache: dict[int, np.ndarray] = {}
        self._order: list[int] = []
        self._max_cache = max(1, int(max_cache))
        self._index = 0

        super().__init__(self._frame(0), **kwargs)

    # ------------------------------------------------------------------ setup

    @staticmethod
    def _target_size(src_w, src_h, width, height, max_width):
        if width and height:
            w, h = int(width), int(height)
        elif width:
            w = int(width)
            h = max(1, round(src_h * w / src_w))
        elif height:
            h = int(height)
            w = max(1, round(src_w * h / src_h))
        elif max_width and src_w > max_width:
            w = int(max_width)
            h = max(1, round(src_h * w / src_w))
        else:
            w, h = int(src_w), int(src_h)
        return _even(w), _even(h)

    def _extract(self, path: Path, out_w: int, out_h: int) -> None:
        for old in self._tmpdir.glob("*.jpg"):
            old.unlink()
        cmd = [
            "ffmpeg", "-v", "error", "-y",
            "-ss", f"{self.start:.6f}", "-i", str(path),
            "-t", f"{self.end - self.start:.6f}", "-an",
            "-vf", f"fps={self.fps},scale={out_w}:{out_h}:flags=lanczos",
            "-q:v", "3", str(self._tmpdir / "%06d.jpg"),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError as exc:  # pragma: no cover - environment guard
            raise RuntimeError("ffmpeg is required to extract video frames") from exc
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{proc.stderr.strip()}")

    # ------------------------------------------------------------------ frames

    def _frame(self, index: int) -> np.ndarray:
        if index in self._cache:
            self._order.remove(index)
            self._order.append(index)
            return self._cache[index]
        from PIL import Image

        arr = np.array(Image.open(self._files[index]).convert("RGBA"))
        self._cache[index] = arr
        self._order.append(index)
        while len(self._order) > self._max_cache:
            old = self._order.pop(0)
            self._cache.pop(old, None)
        return arr

    @property
    def frame_count(self) -> int:
        return len(self._files)

    def set_time(self, t: float) -> "VideoMobject":
        """Show the frame at clip-local time ``t`` (seconds)."""
        n = len(self._files)
        if self.loop:
            i = int(max(0.0, t) * self.fps) % n
        else:
            i = min(n - 1, max(0, int(max(0.0, t) * self.fps)))
        self._index = i
        self.pixel_array = self._frame(i)
        return self

    def play(self, run_time: float | None = None, rate_func=linear) -> "PlayVideo":
        """Return an animation that plays the whole clip."""
        return PlayVideo(self, run_time=run_time or self.duration, rate_func=rate_func)

    # ------------------------------------------------------------------ cleanup

    def close(self) -> None:
        if self._owns_dir and getattr(self, "_tmpdir", None):
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None

    def __del__(self):  # pragma: no cover - best effort
        try:
            self.close()
        except Exception:
            pass


class PlayVideo(Animation):
    """Linear playback for :class:`VideoMobject`.

    ``run_time`` defaults to the clip duration, so ``self.play(clip.play())``
    runs at source speed.
    """

    def __init__(self, mobject: VideoMobject, run_time: float | None = None, **kwargs) -> None:
        if run_time is None:
            run_time = mobject.duration
        kwargs.setdefault("rate_func", linear)
        super().__init__(mobject, run_time=run_time, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        self.mobject.set_time(alpha * self.mobject.duration)
