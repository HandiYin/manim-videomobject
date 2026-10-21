import os

import pytest

from manim_videomobject import VideoMobject

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_RENDER_TESTS") != "1",
    reason="set RUN_RENDER_TESTS=1 to run the slow Manim render test",
)


def test_render_mp4(video, tmp_path):
    from manim import Scene, config

    class Demo(Scene):
        def construct(self):
            clip = VideoMobject(video, max_width=320).scale_to_fit_width(4)
            self.add(clip)
            self.play(clip.play(run_time=1.0))

    config.media_dir = str(tmp_path)
    config.pixel_width = 320
    config.pixel_height = 240
    config.frame_rate = 15
    Demo().render()
    outputs = list(tmp_path.rglob("*.mp4"))
    assert outputs, "Manim produced no output"
    assert outputs[0].stat().st_size > 0
