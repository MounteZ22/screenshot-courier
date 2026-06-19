"""Configuration management with DPAPI encryption for secrets."""

from __future__ import annotations

import json
import os
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import win32crypt
except ImportError:
    win32crypt = None
    logger.warning("pywin32 not installed — secrets will be stored in plain text")

DEFAULT_CONFIG = {
    "screenshot": {
        "interval_minutes": 15,
        "quality": 80,
        "output_dir": "",
    },
    "feishu": {
        "enabled": True,
        "active_binding_id": "",
        "bindings": [],
    },
    "email": {
        "enabled": False,
        "sender": "",
        "smtp_host": "",
        "smtp_port": 465,
        "recipient": "",
    },
    "storage": {
        "retention_days": 30,
        "max_size_gb": 5,
        "auto_clean": True,
    },
    "general": {
        "auto_start": False,
        "minimize_to_tray": True,
        "keep_awake": True,
        "log_level": "INFO",
    },
}


class ConfigManager:
    """Manages config.json (plain) and secrets.dat (DPAPI-encrypted)."""

    def __init__(self, config_dir: str | None = None):
        if config_dir is None:
            config_dir = os.path.join(os.environ.get("APPDATA", ""), "ScreenshotCourier")
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self._config_dir / "config.json"
        self._secrets_path = self._config_dir / "secrets.dat"
        self._config: dict = {}
        self._secrets: dict = {}
        self._load()

    @property
    def config_dir(self) -> Path:
        return self._config_dir

    def _load(self):
        """Load config and secrets from disk."""
        if self._config_path.exists():
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        else:
            self._config = json.loads(json.dumps(DEFAULT_CONFIG))

        if self._secrets_path.exists():
            with open(self._secrets_path, "rb") as f:
                raw = f.read()
            try:
                if win32crypt is not None:
                    decrypted = self._try_decrypt_secrets(raw)
                    self._secrets = json.loads(decrypted.decode("utf-8"))
                else:
                    # Fallback: plain JSON (no DPAPI)
                    self._secrets = json.loads(raw.decode("utf-8"))
            except Exception:
                logger.warning(
                    "Failed to decrypt secrets.dat, starting with empty secrets. "
                    "If this persists, delete %s and re-bind Feishu recipients.",
                    self._secrets_path,
                )
                self._secrets = {}

    @staticmethod
    def _try_decrypt_secrets(raw: bytes) -> bytes:
        """Try multiple CryptUnprotectData parameter combinations for backward compat.

        pywin32 signature: CryptUnprotectData(DataIn, OptionalEntropy, Reserved,
        PromptStruct, Flags).  Flags must be int (0), not None.
        """
        variants = [
            # (entropy, reserved, prompt_struct, flags)
            (None, None, None, 0),   # standard
            ("",  None, None, 0),     # empty entropy
            (None, "",  None, 0),     # empty reserved
        ]
        last_err = None
        for entropy, reserved, prompt, flags in variants:
            try:
                result = win32crypt.CryptUnprotectData(
                    raw, entropy, reserved, prompt, flags
                )
                return result[1]
            except Exception as e:
                last_err = e
                continue
        raise last_err or RuntimeError("All decryption variants failed")

    def save(self):
        """Persist config and secrets to disk."""
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)
        self._save_secrets()

    def _save_secrets(self):
        """Encrypt and save secrets to disk."""
        data = json.dumps(self._secrets).encode("utf-8")
        if win32crypt is not None:
            # CryptProtectData(DataIn, DataDescr, OptionalEntropy, Reserved, PromptStruct)
            # 5th positional = PromptStruct, must be None (NOT int like CryptUnprotectData)
            encrypted = win32crypt.CryptProtectData(data, None, None, None, None)
            with open(self._secrets_path, "wb") as f:
                f.write(encrypted)
        else:
            # Fallback: store as plain JSON
            with open(self._secrets_path, "wb") as f:
                f.write(data)

    # --- Config access ---

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a config value by dot-separated path, e.g. 'screenshot.interval_minutes'."""
        keys = key_path.split(".")
        node = self._config
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return node

    def set(self, key_path: str, value: Any):
        """Set a config value by dot-separated path."""
        keys = key_path.split(".")
        node = self._config
        for k in keys[:-1]:
            if k not in node:
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value

    def get_full_config(self) -> dict:
        """Return a copy of the full config (without secrets)."""
        return json.loads(json.dumps(self._config))

    def update_config(self, new_config: dict):
        """Replace the full config dict."""
        self._config = new_config

    # --- Secrets access ---

    def get_secret(self, key_path: str, default: Any = None) -> Any:
        """Get a secret value by dot-separated path."""
        keys = key_path.split(".")
        node = self._secrets
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return node

    def set_secret(self, key_path: str, value: Any):
        """Set a secret value by dot-separated path and persist immediately."""
        keys = key_path.split(".")
        node = self._secrets
        for k in keys[:-1]:
            if k not in node:
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value
        try:
            self._save_secrets()
        except Exception:
            logger.exception("Failed to save secrets.dat — secret may be lost after restart")

    def delete_secret(self, key_path: str):
        """Delete a secret by dot-separated path."""
        keys = key_path.split(".")
        node = self._secrets
        for k in keys[:-1]:
            if k not in node:
                return
            node = node[k]
        node.pop(keys[-1], None)
        self._save_secrets()
