"""Email fallback sender using yagmail."""

from __future__ import annotations

import logging
from pathlib import Path

import yagmail

logger = logging.getLogger(__name__)


def send_email(image_path: str | Path, smtp_cfg: dict):
    """Send a screenshot via email as fallback.

    Args:
        image_path: Path to the screenshot file.
        smtp_cfg: Dict with keys: sender, password, smtp_host, smtp_port, recipient.
    """
    image_path = str(image_path)
    yag = yagmail.SMTP(
        user=smtp_cfg["sender"],
        password=smtp_cfg["password"],
        host=smtp_cfg["smtp_host"],
        port=smtp_cfg.get("smtp_port", 465),
    )
    yag.send(
        to=smtp_cfg["recipient"],
        subject="实验屏幕截图",
        contents="当前实验屏幕截图如下:",
        attachments=image_path,
    )
    logger.info("Email sent to %s", smtp_cfg["recipient"])
