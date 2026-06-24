from __future__ import annotations

from PIL import Image, ImageFilter


def level_to_block_size(level: int, width: int, height: int) -> int:
    """Map slider level (1-100) to pixel block size."""
    level = max(1, min(100, level))
    max_side = max(width, height)
    # Level 1 -> small blocks (~2px), level 100 -> large blocks (~max_side/8)
    min_block = 2
    max_block = max(min_block, max_side // 8)
    return int(min_block + (level - 1) / 99 * (max_block - min_block))


def pixelize(image: Image.Image, level: int, smooth: bool = False) -> Image.Image:
    """
    Pixelize image.

    Without smoothing: downscale with NEAREST, upscale with NEAREST (sharp blocks).
    With smoothing: block-average colors, then optional light blur on edges.
    """
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")

    width, height = image.size
    block_size = level_to_block_size(level, width, height)

    if not smooth:
        small_w = max(1, width // block_size)
        small_h = max(1, height // block_size)
        small = image.resize((small_w, small_h), Image.Resampling.NEAREST)
        return small.resize((width, height), Image.Resampling.NEAREST)

    return _pixelize_smooth(image, block_size)


def _pixelize_smooth(image: Image.Image, block_size: int) -> Image.Image:
    """Average colors inside each block for softer pixelation."""
    width, height = image.size
    has_alpha = image.mode == "RGBA"
    base = image.convert("RGBA")
    pixels = base.load()
    result = Image.new("RGBA", (width, height))
    out = result.load()

    for y in range(0, height, block_size):
        for x in range(0, width, block_size):
            x2 = min(x + block_size, width)
            y2 = min(y + block_size, height)

            r = g = b = a = 0
            count = 0
            for py in range(y, y2):
                for px in range(x, x2):
                    pr, pg, pb, pa = pixels[px, py]
                    r += pr
                    g += pg
                    b += pb
                    a += pa
                    count += 1

            avg = (r // count, g // count, b // count, a // count)
            for py in range(y, y2):
                for px in range(x, x2):
                    out[px, py] = avg

    if block_size >= 4:
        result = result.filter(ImageFilter.GaussianBlur(radius=0.6))

    if not has_alpha:
        return result.convert("RGB")
    return result
