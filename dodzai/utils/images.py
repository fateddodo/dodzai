"""Image utility helpers."""
from __future__ import annotations

import base64
import random

from .paths import app_media_dir

try:  # pragma: no cover - optional dependency
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFont = None  # type: ignore


def _random_color() -> tuple[int, int, int]:
    return tuple(random.randint(64, 200) for _ in range(3))


def create_placeholder_image(prompt: str, *, suffix: str = "-placeholder.png") -> str:
    """Create a simple placeholder image containing the prompt text."""

    media_dir = app_media_dir()
    media_dir.mkdir(parents=True, exist_ok=True)
    filename = f"image-{abs(hash(prompt)) % (10 ** 8)}{suffix}"
    path = media_dir / filename

    if Image is None:  # pragma: no cover - pillow missing
        path.write_bytes(b"")
        return str(path)

    image = Image.new("RGB", (768, 512), color=_random_color())
    draw = ImageDraw.Draw(image)
    title = prompt[:120] or "DodzAI"
    text = "\n".join(title[i : i + 32] for i in range(0, len(title), 32))

    font = None
    if ImageFont is not None:
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except Exception:
            font = ImageFont.load_default()
    draw.multiline_text((24, 24), text, fill="white", font=font)
    image.save(path)
    return str(path)


def save_base64_image(data: str, *, suffix: str = "-image.png") -> str:
    media_dir = app_media_dir()
    media_dir.mkdir(parents=True, exist_ok=True)
    path = media_dir / f"image-{random.randint(0, 999999)}{suffix}"
    path.write_bytes(base64.b64decode(data))
    return str(path)


def save_base64_audio(data: str, *, suffix: str = "-audio.mp3") -> str:
    media_dir = app_media_dir()
    media_dir.mkdir(parents=True, exist_ok=True)
    path = media_dir / f"audio-{random.randint(0, 999999)}{suffix}"
    path.write_bytes(base64.b64decode(data))
    return str(path)
