#!/usr/bin/env bash
# Create a 4-second 1280x720 demo clip for examples/play_clip.py
set -euo pipefail
cd "$(dirname "$0")"
ffmpeg -v error -y -f lavfi -i "testsrc2=size=1280x720:rate=30" -t 4 \
  -pix_fmt yuv420p demo.mp4
echo "wrote $(pwd)/demo.mp4"
