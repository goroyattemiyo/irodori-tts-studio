#!/usr/bin/env bash
set -e

echo "=== Install ffmpeg ==="
apt-get update -y
apt-get install -y ffmpeg

echo "=== Install uv / pydub ==="
pip install -U uv pydub

echo "=== Setup Irodori-TTS ==="
cd /content/Irodori-TTS
uv sync --extra cu128

echo "=== Setup complete ==="
