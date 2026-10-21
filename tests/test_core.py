import numpy as np
import pytest
from PIL import Image

from manim_videomobject import PlayVideo, VideoMobject, ensure_pillow_compat


def test_basic_playback(video):
    clip = VideoMobject(video, max_width=320)
    assert 28 <= clip.frame_count <= 32
    assert clip.duration == pytest.approx(clip.frame_count / clip.fps)
    a = clip.set_time(0.0).pixel_array.copy()
    b = clip.set_time(0.5).pixel_array
    assert a.shape == b.shape
    assert not np.array_equal(a, b)


def test_trim(video):
    clip = VideoMobject(video, start=0.2, end=0.8, max_width=160)
    assert clip.frame_count == pytest.approx(18, abs=2)
    assert clip.frame_width_px == 160
    assert clip.frame_height_px == 120


def test_loop_wraps(video):
    clip = VideoMobject(video, loop=True, max_width=160)
    a = clip.set_time(0.1).pixel_array.copy()
    b = clip.set_time(1.1).pixel_array
    assert np.array_equal(a, b)


def test_play_animation(video):
    clip = VideoMobject(video, max_width=160)
    anim = clip.play(run_time=1.0)
    assert isinstance(anim, PlayVideo)
    shapes = set()
    frames = []
    for alpha in (0.0, 0.5, 1.0):
        anim.interpolate_mobject(alpha)
        frames.append(clip.pixel_array.copy())
        shapes.add(clip.pixel_array.shape)
    assert len(shapes) == 1
    assert not np.array_equal(frames[0], frames[-1])


def test_bad_inputs(video):
    with pytest.raises(FileNotFoundError):
        VideoMobject(video.with_name("missing.mp4"))
    with pytest.raises(ValueError):
        VideoMobject(video, start=0.8, end=0.2)


def test_pillow_rgba_patch():
    ensure_pillow_compat()
    img = Image.fromarray(np.zeros((6, 8)), mode="RGBA")
    assert img.size == (8, 6)
    assert img.mode == "RGBA"
