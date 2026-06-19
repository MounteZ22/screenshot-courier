"""Local screenshot storage with auto-cleanup."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def build_shot_filename(now: datetime | None = None) -> str:
    """Build a timestamped filename: 2026-06-19_141530.jpg"""
    now = now or datetime.now()
    return now.strftime("%Y-%m-%d_%H%M%S") + ".jpg"


def get_output_dir(configured_dir: str) -> Path:
    """Return the output directory, creating it if needed."""
    if configured_dir:
        d = Path(configured_dir)
    else:
        d = Path.home() / "Pictures" / "ScreenshotCourier"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cleanup_old_screenshots(
    output_dir: Path,
    retention_days: int = 30,
    max_size_gb: float = 5.0,
    auto_clean: bool = True,
):
    """Delete oldest screenshots that exceed retention policy.

    Args:
        output_dir: Directory containing screenshots.
        retention_days: Max age in days (0 = no limit).
        max_size_gb: Max total size in GB (0 = no limit).
        auto_clean: If False, skip cleanup entirely.
    """
    if not auto_clean:
        return

    files = sorted(output_dir.glob("*.jpg"), key=lambda f: f.stat().st_mtime)
    if not files:
        return

    now = datetime.now()
    deleted_count = 0

    # Phase 1: remove files older than retention_days
    if retention_days > 0:
        cutoff = now - timedelta(days=retention_days)
        for f in files[:]:
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                try:
                    f.unlink()
                    files.remove(f)
                    deleted_count += 1
                except OSError as e:
                    logger.warning("Failed to delete %s: %s", f, e)

    # Phase 2: enforce total size limit
    if max_size_gb > 0:
        max_bytes = max_size_gb * 1024 * 1024 * 1024
        total_size = sum(f.stat().st_size for f in files)
        while total_size > max_bytes and files:
            oldest = files.pop(0)
            try:
                total_size -= oldest.stat().st_size
                oldest.unlink()
                deleted_count += 1
            except OSError as e:
                logger.warning("Failed to delete %s: %s", oldest, e)

    if deleted_count:
        logger.info("Cleaned up %d old screenshots from %s", deleted_count, output_dir)
