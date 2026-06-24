"""Pickle-safe helpers for subprocess pixelization."""

from __future__ import annotations

import io

from PIL import Image

from pixelizer_core import pixelize


def pixelize_bytes(source_bytes: bytes, level: int, smooth: bool) -> bytes:
    source = Image.open(io.BytesIO(source_bytes))
    result = pixelize(source, level, smooth=smooth)
    output = io.BytesIO()
    result.save(output, format="PNG")
    return output.getvalue()
