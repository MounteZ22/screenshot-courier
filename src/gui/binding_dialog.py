"""Dialog for adding a new Feishu binding via registerApp QR code scan."""

import io
import logging
import threading

import lark_oapi as lark
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QTextEdit,
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPixmap, QImage

logger = logging.getLogger(__name__)


class BindingDialog(QDialog):
    """Dialog for creating a new Feishu binding via registerApp."""

    binding_added = Signal(str, str, str, str, str)  # label, app_id, app_secret, open_id, email

    # Internal signals for cross-thread UI updates
    _sig_set_qr_pixmap = Signal(QPixmap)
    _sig_update_status = Signal(str)
    _sig_update_info = Signal(str)
    _sig_binding_success = Signal(str, str, str, str, str)  # label, app_id, app_secret, open_id, email
    _sig_enable_btn = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增飞书绑定")
        self.setMinimumWidth(450)
        self._cancel_event = threading.Event()
        self._setup_ui()

        # Connect internal signals to UI slots
        self._sig_set_qr_pixmap.connect(self._set_qr_pixmap)
        self._sig_update_status.connect(self.status_text.append)
        self._sig_update_info.connect(self.info_label.setText)
        self._sig_binding_success.connect(self._on_binding_success)
        self._sig_enable_btn.connect(self.bind_btn.setEnabled)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Label input
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel("姓名备注:"))
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("如：张三")
        label_layout.addWidget(self.label_input)
        layout.addLayout(label_layout)

        # Email input (optional, for fallback notification)
        email_layout = QHBoxLayout()
        email_layout.addWidget(QLabel("备用邮箱:"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("选填，飞书失败时邮件通知")
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)

        # Info area
        self.info_label = QLabel("点击下方按钮开始绑定流程")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # QR code display area
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setMinimumSize(256, 256)
        self.qr_label.setStyleSheet("border: 1px solid #ccc; background: white;")
        self.qr_label.setText("二维码将在此显示")
        layout.addWidget(self.qr_label)

        # Status text
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(80)
        layout.addWidget(self.status_text)

        # Buttons
        btn_layout = QHBoxLayout()
        self.bind_btn = QPushButton("开始绑定")
        self.bind_btn.clicked.connect(self._on_bind)
        btn_layout.addWidget(self.bind_btn)

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self._on_close)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def _on_bind(self):
        label = self.label_input.text().strip()
        if not label:
            QMessageBox.warning(self, "提示", "请输入姓名备注")
            return

        self.bind_btn.setEnabled(False)
        self._cancel_event.clear()
        self.info_label.setText("正在初始化飞书绑定...")
        self.status_text.append("开始绑定流程...")

        email = self.email_input.text().strip()
        thread = threading.Thread(target=self._do_register, args=(label, email), daemon=True)
        thread.start()

    def _on_close(self):
        """Cancel any in-progress registration and close."""
        self._cancel_event.set()
        self.close()

    def _do_register(self, label: str, email: str = ""):
        """Run lark.register_app in background thread."""
        try:
            self._sig_update_status.emit("正在调用飞书 registerApp...")

            def on_qr_code(info):
                url = info["url"]
                expire_in = info.get("expire_in", 600)
                self._sig_update_info.emit(f"请用飞书扫码（{expire_in}秒内有效）")
                self._sig_update_status.emit(f"扫码链接: {url}")
                self._generate_qr_pixmap(url)

            def on_status_change(info):
                status = info.get("status", "polling")
                if status == "slow_down":
                    self._sig_update_status.emit("网络较慢，正在重试...")
                elif status == "domain_switched":
                    self._sig_update_status.emit("正在切换域名...")

            result = lark.register_app(
                on_qr_code=on_qr_code,
                on_status_change=on_status_change,
                source="screenshot-courier",
                cancel_event=self._cancel_event,
                app_preset={
                    "name": f"ScreenshotCourier-{label}",
                    "desc": f"截图快递 - {label} 的实验监控机器人",
                },
            )

            if not isinstance(result, dict):
                self._sig_update_status.emit(
                    f"绑定失败：registerApp 返回了非预期的结果类型 ({type(result).__name__})，"
                    f"请检查 lark-oapi SDK 版本"
                )
                logger.error("registerApp returned non-dict: %s", type(result))
                return

            # Extract credentials
            app_id = result.get("client_id", "")
            app_secret = result.get("client_secret", "")
            user_info = result.get("user_info", {}) or {}
            open_id = user_info.get("open_id", "") if isinstance(user_info, dict) else ""

            if not app_id or not app_secret:
                self._sig_update_status.emit(
                    "绑定失败：未获取到应用凭证（app_id 或 app_secret 为空）。\n"
                    "可能原因：扫码取消、SDK 兼容性问题、或飞书应用创建限制。\n"
                    "备选方案：在飞书开放平台手动创建应用，然后在「高级设置 > 飞书 > 手动配置」中填写。"
                )
                self._sig_update_info.emit("扫码绑定未成功，可尝试手动配置或重试")
                logger.warning(
                    "registerApp returned empty credentials: result keys=%s",
                    list(result.keys()) if result else "none",
                )
                return

            if not open_id:
                self._sig_update_status.emit("警告：未获取到 open_id，可能需要手动配置")

            self._sig_binding_success.emit(label, app_id, app_secret, open_id, email)

        except lark.RegisterAppError as e:
            self._sig_update_status.emit(
                f"绑定失败: {e}\n备选方案：在「高级设置 > 飞书 > 手动配置」中填写应用信息。"
            )
            logger.error("registerApp failed: %s", e)
        except lark.AppAccessDeniedError:
            self._sig_update_status.emit("用户取消了授权，可重新尝试或使用手动配置")
        except lark.AppExpiredError:
            self._sig_update_status.emit("二维码已过期，请重新绑定")
        except Exception as e:
            self._sig_update_status.emit(
                f"绑定失败: {e}\n备选方案：在「高级设置 > 飞书 > 手动配置」中填写应用信息。"
            )
            logger.error("Binding failed: %s", e, exc_info=True)
        finally:
            self._sig_enable_btn.emit(True)

    def _generate_qr_pixmap(self, url: str):
        """Generate a QR code QPixmap from URL and emit to main thread."""
        try:
            import qrcode

            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert PIL Image to QPixmap
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            qimg = QImage()
            qimg.loadFromData(buf.read())
            pixmap = QPixmap.fromImage(qimg)
            self._sig_set_qr_pixmap.emit(pixmap)
        except Exception as e:
            logger.error("QR generation failed: %s", e)
            self._sig_update_status.emit(f"二维码生成失败: {e}")

    @Slot(QPixmap)
    def _set_qr_pixmap(self, pixmap: QPixmap):
        self.qr_label.setPixmap(pixmap.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    @Slot(str, str, str, str, str)
    def _on_binding_success(self, label: str, app_id: str, app_secret: str, open_id: str, email: str):
        self.binding_added.emit(label, app_id, app_secret, open_id, email)
        self.status_text.append(f"绑定成功: {label}")
        self.info_label.setText("绑定完成！可以关闭此窗口。")
        QMessageBox.information(self, "成功", f"接收人 '{label}' 绑定成功！")
