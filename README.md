# manim-videomobject

[![CI](https://github.com/HandiYin/manim-videomobject/actions/workflows/ci.yml/badge.svg)](https://github.com/HandiYin/manim-videomobject/actions/workflows/ci.yml)

A drop-in `VideoMobject` for [Manim Community](https://www.manim.community/). Manim CE ships `ImageMobject`, `SVGMobject` and `Text`, but no video mobject — this package fills that gap by decoding a clip with ffmpeg into a frame sequence and playing it through the normal `ImageMobject` render path.

```python
from manim import *
from manim_videomobject import VideoMobject

class Demo(Scene):
    def construct(self):
        clip = VideoMobject("take.mp4", start=2, end=8).scale_to_fit_width(10)
        self.add(clip)
        self.play(clip.play())
```

## Features

- Real motion: frames advance with the animation timeline, so fades, transforms and camera moves compose normally.
- Trim, loop, choose fps, downscale (`max_width` / `width` / `height`).
- Audio is ignored; the output is a normal silent Manim render.
- Lazy frame loading with a bounded LRU cache.
- Optional JPEG frame cache you can keep between renders (`cache_dir=`).
- Works around the Manim ≤ 0.22 + Pillow ≥ 11 RGBA canvas bug.
- No OpenCV / PyAV dependency: only `ffmpeg` and `ffprobe` binaries.

## Install

```bash
pip install git+https://github.com/HandiYin/manim-videomobject.git
```

or for development:

```bash
git clone https://github.com/HandiYin/manim-videomobject.git
cd manim-videomobject
pip install -e ".[test]"
```

Requirements: Python ≥ 3.9, Manim ≥ 0.18, `ffmpeg`/`ffprobe` on `PATH`.

## Usage

### Trim and play

```python
clip = VideoMobject("take.mp4", start=2.0, end=8.0)
clip.scale_to_fit_width(10).move_to(ORIGIN)
self.add(clip)
self.play(clip.play())          # run_time defaults to clip duration
```

### Loop under other animations

```python
bg = VideoMobject("loop.mp4", loop=True, max_width=1280)
bg.scale_to_fit_width(14)
self.add(bg)
self.play(bg.play(run_time=12), FadeIn(title))
```

### Manual time control

```python
clip = VideoMobject("take.mp4", fps=15, max_width=960)
clip.set_time(3.5)              # clip-local seconds
self.add(clip)
```

### Keep the extracted frames

```python
clip = VideoMobject("take.mp4", cache_dir="build/frames/take")
# reuse later: VideoMobject(..., cache_dir="build/frames/take") re-extracts into the same dir
```

## API

`VideoMobject(file_path, *, fps=None, start=0.0, end=None, loop=False, width=None, height=None, max_width=None, cache_dir=None, max_cache=48, patch_pillow=True, **kwargs)`

| Member | Meaning |
|---|---|
| `duration` | Clip duration in seconds after trimming |
| `fps` | Playback frame rate |
| `frame_count` | Number of extracted frames |
| `frame_width_px`, `frame_height_px` | Extracted frame size |
| `set_time(t)` | Show clip-local time `t` |
| `play(run_time=None, rate_func=linear)` | Return a `PlayVideo` animation |
| `close()` | Delete the temporary frame directory |

`PlayVideo(mobject, run_time=None)` is a normal `Animation`; it drives `set_time(alpha * duration)`.

## How it works

1. `ffprobe` reads size, frame rate and duration.
2. `ffmpeg -ss … -t … -vf fps=…,scale=…` writes a JPEG sequence to a temporary directory (or `cache_dir`).
3. `VideoMobject` subclasses `ImageMobject`; `set_time()` swaps `pixel_array` for the requested frame.
4. `PlayVideo` interpolates `alpha → time`, so the clip plays exactly with Manim's clock.

This keeps the whole thing inside the regular Cairo render path: no second video pipeline, no codec-specific rendering code.

## Performance notes

- Frames are decoded lazily; `max_cache` controls how many decoded RGBA frames stay in RAM.
- For explainer clips, downsample: `max_width=960` is usually enough for a 1080p composition and cuts decode cost by ~4×.
- `fps=15` halves the work again for slow-motion source material.
- Extraction is a one-time cost per clip; use `cache_dir` to reuse frames across renders.

Measured on the weekly-brief project (Manim 0.22, 1080p30, 6 s clips): 180-frame extraction < 2 s, rendering stays within ~10% of the equivalent static-image scene.

## Limitations

- **No audio.** Manim has no audio mixing pipeline; add sound in post.
- **Short clips.** Extraction pre-materializes every frame; a 10-minute 1080p video is a bad fit. Trim first.
- **No alpha video.** JPEG frames are opaque; use a chroma-key or a PNG-sequence fork if you need transparency.
- **Frame-accurate but not frame-perfect.** ffmpeg re-times to a constant `fps`; variable-frame-rate sources are normalized.

## Pillow compatibility

Manim ≤ 0.22 calls `Image.fromarray(np.zeros((h, w)), mode="RGBA")` inside `Camera.display_image_mobject`; Pillow ≥ 11 rejects the float64 array. `VideoMobject` calls `ensure_pillow_compat()` by default, which narrows that one call shape to a uint8 RGBA canvas. Disable with `patch_pillow=False` if you already patch it yourself.

## Development

```bash
ffmpeg -version
pip install -e ".[test]"
pytest -q
RUN_RENDER_TESTS=1 pytest -q tests/test_render.py
```

The render test needs a working Manim/Cairo install and is skipped by default.

## License

MIT © 2026 HandiYin
