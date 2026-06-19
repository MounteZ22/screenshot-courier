"""Screen capture engine using MSS."""

from __future__ import annotations

import logging
from pathlib import Path

import mss
from PIL import Image

logger = logging.getLogger(__name__)


def capture_screen(output_path: str | Path, quality: int = 80) -> Path:
    """Capture the primary monitor and save as JPEG.

    Args:
        output_path: Where to save the screenshot.
        quality: JPEG quality (1-100).

    Returns:
        Path to the saved screenshot.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with mss.mss() as sct:
        monitor = sct.monitors[1]  # primary monitor
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        img.save(str(output_path), "JPEG", quality=quality)

    logger.debug("Screenshot saved: %s", output_path)
    return output_path
