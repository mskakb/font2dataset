#!/usr/bin/env bash
set -euo pipefail # Error handling

uv add \
  Pillow \
  fonttools \
  datasets \
  tqdm \
  pyyaml \
  numpy
