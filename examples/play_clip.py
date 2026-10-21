"""Minimal Manim scene that plays demo.mp4 with VideoMobject."""

from manim import *

from manim_videomobject import VideoMobject


class Demo(Scene):
    def construct(self):
        clip = VideoMobject("demo.mp4", start=0, end=4, max_width=1280)
        clip.scale_to_fit_width(12)
        self.add(clip)
        self.play(clip.play())


if __name__ == "__main__":
    # python examples/play_clip.py  (renders Demo to media/)
    pass
