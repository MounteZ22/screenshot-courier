"""Feishu (Lark) client for image upload and message sending via REST API."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

FEISHU_BASE = "https://open.feishu.cn/open-apis"


class FeishuClient:
    """Feishu client with automatic token refresh via REST API."""

    def __init__(self, app_id: str, app_secret: str):
        self._app_id = app_id
        self._app_secret = app_secret
        self._token: str = ""
        self._token_expires_at: float = 0

    def _ensure_token(self):
        """Obtain or refresh tenant_access_token."""
        if self._token and time.time() < self._token_expires_at - 300:
            return
        resp = requests.post(
            f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
            json={"app_id": self._app_id, "app_secret": self._app_secret},
            timeout=15,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(
                f"飞书获取 token 失败: code={data.get('code')}, msg={data.get('msg')}"
            )
        self._token = data["tenant_access_token"]
        self._token_expires_at = time.time() + data.get("expire", 7200)
        logger.debug("Feishu token refreshed")

    def send_image(self, image_path: str | Path, receive_id: str, receive_id_type: str = "open_id") -> str:
        """Upload image and send as message. Returns message_id."""
        self._ensure_token()
        image_path = Path(image_path)
        headers = {"Authorization": f"Bearer {self._token}"}

        # Step 1: Upload image
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{FEISHU_BASE}/im/v1/images",
                headers=headers,
                files={"image": (image_path.name, f, "image/jpeg")},
                data={"image_type": "message"},
                timeout=30,
            )
        upload_data = resp.json()
        if upload_data.get("code") != 0:
            raise RuntimeError(
                f"飞书图片上传失败: code={upload_data.get('code')}, msg={upload_data.get('msg')}"
            )
        image_key = upload_data["data"]["image_key"]

        # Step 2: Send message
        resp = requests.post(
            f"{FEISHU_BASE}/im/v1/messages",
            headers={**headers, "Content-Type": "application/json"},
            params={"receive_id_type": receive_id_type},
            json={
                "receive_id": receive_id,
                "msg_type": "image",
                "content": json.dumps({"image_key": image_key}),
            },
            timeout=15,
        )
        msg_data = resp.json()
        if msg_data.get("code") != 0:
            raise RuntimeError(
                f"飞书消息发送失败: code={msg_data.get('code')}, msg={msg_data.get('msg')}"
            )

        message_id = msg_data["data"]["message_id"]
        logger.info("Image sent via Feishu: message_id=%s", message_id)
        return message_id
