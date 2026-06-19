"""Manage Feishu binding list: add, remove, switch, persist."""

import logging
import uuid
from datetime import datetime
from typing import Any

from ..config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

MAX_BINDINGS = 10


class BindingManager:
    """Multi-binding manager for Feishu recipients."""

    def __init__(self, config_manager: ConfigManager):
        self._cm = config_manager

    def _get_bindings(self) -> list[dict]:
        return self._cm.get("feishu.bindings", [])

    def _save_bindings(self, bindings: list[dict]):
        self._cm.set("feishu.bindings", bindings)
        self._cm.save()

    def list_bindings(self) -> list[dict]:
        """Return all bindings (label, id, email, created_at — no secrets)."""
        return [
            {
                "id": b["id"],
                "label": b["label"],
                "receive_id": b.get("receive_id", ""),
                "email": b.get("email", ""),
                "mode": b.get("mode", "private"),
                "created_at": b.get("created_at", ""),
            }
            for b in self._get_bindings()
        ]

    def get_active_binding_id(self) -> str:
        return self._cm.get("feishu.active_binding_id", "")

    def get_active_binding(self) -> dict | None:
        """Return the currently active binding, or None."""
        active_id = self.get_active_binding_id()
        for b in self._get_bindings():
            if b["id"] == active_id:
                return b
        # Fallback: if active_id is empty/invalid, return first binding
        bindings = self._get_bindings()
        if bindings:
            self._cm.set("feishu.active_binding_id", bindings[0]["id"])
            self._cm.save()
            return bindings[0]
        return None

    def get_active_secrets(self) -> dict | None:
        """Return app_secret for the active binding."""
        active = self.get_active_binding()
        if not active:
            return None
        secret = self._cm.get_secret(f"feishu.bindings.{active['id']}")
        if secret:
            return {
                "app_id": active.get("app_id", ""),
                "app_secret": secret,
                "receive_id": active.get("receive_id", ""),
                "email": active.get("email", ""),
            }
        return None

    def add_binding(
        self,
        label: str,
        app_id: str,
        app_secret: str,
        receive_id: str,
        receive_id_type: str = "open_id",
        mode: str = "private",
        group_chat_id: str = "",
        email: str = "",
    ) -> str:
        """Add a new binding and set it as active. Returns the new binding id."""
        bindings = self._get_bindings()
        if len(bindings) >= MAX_BINDINGS:
            raise ValueError(f"已达绑定上限({MAX_BINDINGS}个)，请先删除不用的接收人")

        binding_id = f"b_{uuid.uuid4().hex[:8]}"
        binding = {
            "id": binding_id,
            "label": label,
            "app_id": app_id,
            "receive_id": receive_id,
            "receive_id_type": receive_id_type,
            "mode": mode,
            "group_chat_id": group_chat_id,
            "email": email,
            "created_at": datetime.now().isoformat(),
        }
        bindings.append(binding)
        self._save_bindings(bindings)
        self._cm.set_secret(f"feishu.bindings.{binding_id}", app_secret)

        # Set as active
        self._cm.set("feishu.active_binding_id", binding_id)
        self._cm.save()

        logger.info("Binding added: %s (%s)", label, binding_id)
        return binding_id

    def switch_binding(self, binding_id: str) -> bool:
        """Switch the active binding. Returns True if successful."""
        for b in self._get_bindings():
            if b["id"] == binding_id:
                self._cm.set("feishu.active_binding_id", binding_id)
                self._cm.save()
                logger.info("Switched to binding: %s", b["label"])
                return True
        logger.warning("Binding not found: %s", binding_id)
        return False

    def remove_binding(self, binding_id: str) -> bool:
        """Remove a binding by id. Returns True if removed."""
        bindings = self._get_bindings()
        new_bindings = [b for b in bindings if b["id"] != binding_id]
        if len(new_bindings) == len(bindings):
            return False

        self._save_bindings(new_bindings)
        self._cm.delete_secret(f"feishu.bindings.{binding_id}")

        # If removed the active one, switch to first available
        if self._cm.get("feishu.active_binding_id") == binding_id:
            if new_bindings:
                self._cm.set("feishu.active_binding_id", new_bindings[0]["id"])
            else:
                self._cm.set("feishu.active_binding_id", "")
            self._cm.save()

        logger.info("Binding removed: %s", binding_id)
        return True

    def get_binding_by_id(self, binding_id: str) -> dict | None:
        """Get a binding by its id."""
        for b in self._get_bindings():
            if b["id"] == binding_id:
                return b
        return None

    def update_binding_secret(self, binding_id: str, app_secret: str) -> bool:
        """Update the app_secret for an existing binding. Returns True if updated."""
        binding = self.get_binding_by_id(binding_id)
        if not binding:
            return False
        self._cm.set_secret(f"feishu.bindings.{binding_id}", app_secret)
        logger.info("Updated secret for binding %s", binding_id)
        return True

    def update_binding_email(self, binding_id: str, email: str) -> bool:
        """Update the email for a binding. Returns True if updated."""
        bindings = self._get_bindings()
        for b in bindings:
            if b["id"] == binding_id:
                b["email"] = email
                self._save_bindings(bindings)
                logger.info("Updated email for binding %s", binding_id)
                return True
        return False
