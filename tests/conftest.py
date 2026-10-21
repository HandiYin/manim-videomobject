import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def video(tmp_path_factory) -> Path:
    """1-second 320x240 testsrc clip at 30 fps."""
    path = tmp_path_factory.mktemp("media") / "testsrc.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30",
            "-t", "1", "-pix_fmt", "yuv420p", str(path),
        ],
        check=True,
    )
    return path
