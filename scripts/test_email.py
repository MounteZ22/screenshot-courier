"""Test email sending with the current app SMTP config. Run with: python scripts/test_email.py"""
import json
import os
import sys
from pathlib import Path

import win32crypt

config_dir = os.path.join(os.environ["APPDATA"], "ScreenshotCourier")
config_path = os.path.join(config_dir, "config.json")
secrets_path = os.path.join(config_dir, "secrets.dat")

# Load config
with open(config_path, encoding="utf-8") as f:
    config = json.load(f)

email_cfg = config.get("email", {})
if not email_cfg.get("enabled"):
    print("邮箱推送未启用（email.enabled=false），请先在设置中启用")
    sys.exit(1)

sender = email_cfg.get("sender", "")
smtp_host = email_cfg.get("smtp_host", "")
smtp_port = email_cfg.get("smtp_port", 465)

# Load password from secrets
with open(secrets_path, "rb") as f:
    raw = f.read()
decrypted = win32crypt.CryptUnprotectData(raw, None, None, None, 0)
secrets = json.loads(decrypted[1].decode("utf-8"))
password = secrets.get("email", {}).get("password", "")

if not all([sender, password, smtp_host]):
    print("SMTP 配置不完整，请检查: 发件邮箱、授权码、SMTP 服务器")
    print(f"  sender={sender}, password={'***' if password else 'EMPTY'}, host={smtp_host}")
    sys.exit(1)

# Determine recipient: active binding's email first, then global
recipient = email_cfg.get("recipient", "")
bindings = config.get("feishu", {}).get("bindings", [])
active_id = config.get("feishu", {}).get("active_binding_id", "")
for b in bindings:
    if b["id"] == active_id:
        recipient = b.get("email", "") or recipient
        break

if not recipient:
    print("未找到收件邮箱。请在设置 → 接收人 → 兜底邮箱中填写")
    sys.exit(1)

print(f"发件: {sender}")
print(f"收件: {recipient}")
print(f"SMTP: {smtp_host}:{smtp_port}")
print(f"授权码: {'***' if password else 'EMPTY'}")

# Send test email
import yagmail

try:
    yag = yagmail.SMTP(user=sender, password=password, host=smtp_host, port=smtp_port)
    yag.send(
        to=recipient,
        subject="[Screenshot Courier] 邮件测试",
        contents="这是 Screenshot Courier 的邮件发送测试。\n\n如果你收到这封邮件，说明邮箱配置正确。",
    )
    yag.close()
    print("\n[OK] 测试邮件发送成功！请检查收件箱。")
except Exception as e:
    print(f"\n[FAIL] 发送失败: {e}")
    sys.exit(1)
