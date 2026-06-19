"""Notification orchestrator: retry + fallback + alert."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from ..config.config_manager import ConfigManager
from ..binding.binding_manager import BindingManager
from .feishu_client import FeishuClient
from .email_client import send_email

logger = logging.getLogger(__name__)

RETRY_DELAYS = [1, 3, 5]  # seconds (short delays to avoid blocking UI)


class NotificationManager:
    """Orchestrates screenshot delivery with retry and email fallback."""

    def __init__(self, config_manager: ConfigManager, binding_manager: BindingManager):
        self._cm = config_manager
        self._bm = binding_manager
        self._feishu_client: FeishuClient | None = None
        self._alert_callback = None  # set by GUI for tray alerts

    def set_alert_callback(self, callback):
        """Set a callback for tray alerts: callback(message: str, level: str)"""
        self._alert_callback = callback

    def _alert(self, message: str, level: str = "warning"):
        logger.log(getattr(logging, level.upper(), logging.WARNING), message)
        if self._alert_callback:
            self._alert_callback(message, level)

    def _get_feishu_client(self) -> FeishuClient:
        """Get or create FeishuClient from active binding."""
        secrets = self._bm.get_active_secrets()
        if not secrets:
            raise RuntimeError("没有可用的飞书绑定")
        if self._feishu_client is None or self._feishu_client._app_id != secrets["app_id"]:
            self._feishu_client = FeishuClient(secrets["app_id"], secrets["app_secret"])
        return self._feishu_client

    def _send_via_feishu(self, image_path: str):
        """Send image through active Feishu binding."""
        binding = self._bm.get_active_binding()
        if not binding:
            raise RuntimeError("没有可用的飞书绑定")
        client = self._get_feishu_client()
        receive_id = binding.get("receive_id", "")
        receive_id_type = binding.get("receive_id_type", "open_id")
        client.send_image(image_path, receive_id, receive_id_type)

    def _send_via_email(self, image_path: str):
        """Send image via email fallback.

        Uses the active binding's email as recipient if global recipient is not set.
        """
        recipient = self._cm.get("email.recipient", "")
        if not recipient:
            # Fall back to active binding's email
            secrets = self._bm.get_active_secrets()
            if secrets:
                recipient = secrets.get("email", "")
        if not recipient:
            raise RuntimeError("未配置收件邮箱，请在设置中填写或在绑定中关联邮箱")

        email_cfg = {
            "sender": self._cm.get("email.sender", ""),
            "password": self._cm.get_secret("email.password", ""),
            "smtp_host": self._cm.get("email.smtp_host", ""),
            "smtp_port": self._cm.get("email.smtp_port", 465),
            "recipient": recipient,
        }
        if not all([email_cfg["sender"], email_cfg["password"], email_cfg["smtp_host"]]):
            raise RuntimeError("邮件发送配置不完整，请在设置中填写 SMTP 信息")
        send_email(image_path, email_cfg)

    def send_screenshot(self, image_path: str | Path):
        """Send screenshot with retry + email fallback.

        Tries Feishu up to 3 times, then falls back to email.
        """
        image_path = str(image_path)
        feishu_enabled = self._cm.get("feishu.enabled", True)
        email_enabled = self._cm.get("email.enabled", False)

        if feishu_enabled:
            for attempt, delay in enumerate(RETRY_DELAYS, 1):
                try:
                    self._send_via_feishu(image_path)
                    return  # success
                except Exception as e:
                    logger.warning("飞书第%d次推送失败: %s", attempt, e)
                    if attempt < len(RETRY_DELAYS):
                        time.sleep(delay)

            # All retries exhausted
            self._alert("飞书推送失败，尝试邮件兜底", level="warning")

        if email_enabled:
            try:
                self._send_via_email(image_path)
                self._alert("飞书推送失败，已改用邮件发送", level="warning")
                return
            except Exception as e:
                logger.error("邮件兜底也失败: %s", e)

        self._alert("推送全部失败，请检查网络/绑定", level="error")

    def test_feishu(self) -> bool:
        """Test Feishu connection by attempting to refresh token."""
        try:
            self._get_feishu_client()._ensure_token()
            return True
        except Exception as e:
            logger.error("飞书连接测试失败: %s", e)
            return False

    def test_email(self) -> bool:
        """Test email config by sending nothing (just connection check)."""
        try:
            email_cfg = {
                "sender": self._cm.get("email.sender", ""),
                "password": self._cm.get_secret("email.password", ""),
                "smtp_host": self._cm.get("email.smtp_host", ""),
                "smtp_port": self._cm.get("email.smtp_port", 465),
            }
            if not all(email_cfg.values()):
                return False
            import yagmail
            yag = yagmail.SMTP(
                user=email_cfg["sender"],
                password=email_cfg["password"],
                host=email_cfg["smtp_host"],
                port=email_cfg["smtp_port"],
            )
            yag.close()
            return True
        except Exception as e:
            logger.error("邮件连接测试失败: %s", e)
            return False
