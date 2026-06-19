"""WeCom (Enterprise WeChat) group robot webhook client — Plan B."""

import base64
import hashlib
import logging
from pathlib import Path
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def send_image_webhook(image_path: str | Path, webhook_url: str):
    """Send a screenshot via WeCom group robot webhook.

    Args:
        image_path: Path to the screenshot file.
        webhook_url: The WeCom bot webhook URL.
    """
    image_path = Path(image_path)
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    base64_str = base64.b64encode(img_bytes).decode("utf-8")
    md5_str = hashlib.md5(img_bytes).hexdigest()

    payload = {
        "msgtype": "image",
        "image": {
            "base64": base64_str,
            "md5": md5_str,
        },
    }

    import json

    data = json.dumps(payload).encode("utf-8")
    req = Request(webhook_url, data=data, headers={"Content-Type": "application/json"})
    resp = urlopen(req, timeout=30)
    result = json.loads(resp.read().decode("utf-8"))

    if result.get("errcode", 0) != 0:
        raise RuntimeError(f"企业微信发送失败: {result}")

    logger.info("Image sent via WeCom webhook")
