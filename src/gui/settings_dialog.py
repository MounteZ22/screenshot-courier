"""Settings dialog for configuring Screenshot Courier."""

import logging

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QFileDialog,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QFrame,
)
from PySide6.QtCore import Qt

from ..config.config_manager import ConfigManager
from ..binding.binding_manager import BindingManager

logger = logging.getLogger(__name__)

INTERVAL_PRESETS = [5, 10, 15, 20, 30, 45, 60]


class SettingsDialog(QDialog):
    """Settings dialog with tabs: 接收人 / 截图 / 通用."""

    def __init__(self, config_manager: ConfigManager, binding_manager: BindingManager, parent=None):
        super().__init__(parent)
        self._cm = config_manager
        self._bm = binding_manager
        self._selected_binding_id: str = ""
        self.setWindowTitle("设置")
        self.setMinimumWidth(560)
        self._setup_ui()
        self._load_settings()

    # ── UI structure ─────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._create_recipient_tab(), "接收人")
        tabs.addTab(self._create_screenshot_tab(), "截图")
        tabs.addTab(self._create_general_tab(), "通用")
        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    # ── 接收人 Tab ──────────────────────────────────────────────

    def _create_recipient_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        splitter = QSplitter(Qt.Horizontal)

        # Left: recipient list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.recipient_list = QListWidget()
        self.recipient_list.currentItemChanged.connect(self._on_recipient_selected)
        left_layout.addWidget(self.recipient_list)

        left_btns = QHBoxLayout()
        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self._add_recipient)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._delete_recipient)
        left_btns.addWidget(add_btn)
        left_btns.addWidget(del_btn)
        left_layout.addLayout(left_btns)
        splitter.addWidget(left)

        # Right: detail panel
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(10, 0, 0, 0)

        form = QFormLayout()

        self.recip_name_input = QLineEdit()
        form.addRow("名称:", self.recip_name_input)

        self.recip_feishu_status = QLabel("飞书状态: —")
        rebind_btn = QPushButton("重新绑定")
        rebind_btn.clicked.connect(self._rebind_feishu)
        feishu_row = QHBoxLayout()
        feishu_row.addWidget(self.recip_feishu_status, 1)
        feishu_row.addWidget(rebind_btn)
        form.addRow("飞书:", feishu_row)

        self.recip_email_input = QLineEdit()
        self.recip_email_input.setPlaceholderText("飞书失败时的兜底收件邮箱")
        form.addRow("兜底邮箱:", self.recip_email_input)

        # Custom SMTP for this recipient
        self.recip_smtp_check = QCheckBox("使用自定义发件邮箱")
        self.recip_smtp_check.toggled.connect(self._on_smtp_toggled)
        form.addRow(self.recip_smtp_check)

        self.recip_smtp_sender = QLineEdit()
        self.recip_smtp_sender.setPlaceholderText("发件邮箱地址")
        self.recip_smtp_sender.setVisible(False)
        form.addRow("  发件邮箱:", self.recip_smtp_sender)

        self.recip_smtp_password = QLineEdit()
        self.recip_smtp_password.setEchoMode(QLineEdit.Password)
        self.recip_smtp_password.setPlaceholderText("授权码")
        self.recip_smtp_password.setVisible(False)
        form.addRow("  授权码:", self.recip_smtp_password)

        smtp_host_row = QHBoxLayout()
        self.recip_smtp_host = QLineEdit()
        self.recip_smtp_host.setPlaceholderText("smtp.qq.com")
        self.recip_smtp_host.setVisible(False)
        smtp_host_row.addWidget(self.recip_smtp_host)
        self.recip_smtp_port = QSpinBox()
        self.recip_smtp_port.setRange(1, 65535)
        self.recip_smtp_port.setValue(465)
        self.recip_smtp_port.setVisible(False)
        smtp_host_row.addWidget(self.recip_smtp_port)
        form.addRow("  服务器:端口:", smtp_host_row)

        self.recip_dir_input = QLineEdit()
        self.recip_dir_input.setPlaceholderText("留空使用全局默认目录")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_recip_dir)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self.recip_dir_input)
        dir_row.addWidget(browse_btn)
        form.addRow("截图目录:", dir_row)

        right_layout.addLayout(form)
        right_layout.addStretch()

        save_btn = QPushButton("保存修改")
        save_btn.clicked.connect(self._save_recipient_detail)
        right_layout.addWidget(save_btn)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        self._refresh_recipient_list()
        return w

    def _refresh_recipient_list(self):
        bindings = self._bm.list_bindings()
        active_id = self._bm.get_active_binding_id()
        self.recipient_list.blockSignals(True)
        self.recipient_list.clear()
        for b in bindings:
            marker = "▶ " if b["id"] == active_id else "  "
            item = QListWidgetItem(f"{marker}{b['label']}")
            item.setData(Qt.UserRole, b["id"])
            self.recipient_list.addItem(item)
        self.recipient_list.blockSignals(False)

        # Restore selection
        if self._selected_binding_id:
            for i in range(self.recipient_list.count()):
                item = self.recipient_list.item(i)
                if item and item.data(Qt.UserRole) == self._selected_binding_id:
                    self.recipient_list.setCurrentItem(item)
                    break
        if not self.recipient_list.currentItem() and self.recipient_list.count() > 0:
            self.recipient_list.setCurrentRow(0)

    def _on_recipient_selected(self, current, previous):
        if current is None:
            self._selected_binding_id = ""
            self._clear_recipient_detail()
            return
        self._selected_binding_id = current.data(Qt.UserRole) or ""
        self._load_recipient_detail()

    def _load_recipient_detail(self):
        binding = self._bm.get_binding_by_id(self._selected_binding_id)
        if not binding:
            self._clear_recipient_detail()
            return
        self.recip_name_input.setText(binding.get("label", ""))
        self.recip_email_input.setText(binding.get("email", ""))
        self.recip_dir_input.setText(binding.get("output_dir", ""))

        # Feishu status
        secret = self._cm.get_secret(f"feishu.bindings.{self._selected_binding_id}")
        if secret:
            self.recip_feishu_status.setText("飞书状态: ✓ 已绑定")
            self.recip_feishu_status.setStyleSheet("color: #4CAF50;")
        else:
            self.recip_feishu_status.setText("飞书状态: ⚠ 密钥缺失")
            self.recip_feishu_status.setStyleSheet("color: #F44336;")

        # SMTP
        smtp_sender = binding.get("smtp_sender", "")
        smtp_host = binding.get("smtp_host", "")
        has_smtp = bool(smtp_sender and smtp_host)
        self.recip_smtp_check.setChecked(has_smtp)
        self.recip_smtp_sender.setText(smtp_sender)
        self.recip_smtp_host.setText(smtp_host)
        self.recip_smtp_port.setValue(binding.get("smtp_port", 465))
        smtp_pwd = self._cm.get_secret(f"feishu.smtp_passwords.{self._selected_binding_id}", "")
        self.recip_smtp_password.setPlaceholderText(
            "已保存（不显示）" if smtp_pwd else "授权码"
        )
        self.recip_smtp_password.clear()
        self._on_smtp_toggled(has_smtp)

    def _on_smtp_toggled(self, checked):
        self.recip_smtp_sender.setVisible(checked)
        self.recip_smtp_password.setVisible(checked)
        self.recip_smtp_host.setVisible(checked)
        self.recip_smtp_port.setVisible(checked)

    def _clear_recipient_detail(self):
        self.recip_name_input.clear()
        self.recip_email_input.clear()
        self.recip_dir_input.clear()
        self.recip_feishu_status.setText("飞书状态: —")
        self.recip_feishu_status.setStyleSheet("")
        self.recip_smtp_check.setChecked(False)
        self.recip_smtp_sender.clear()
        self.recip_smtp_password.clear()
        self.recip_smtp_host.clear()
        self.recip_smtp_port.setValue(465)

    def _save_recipient_detail(self):
        if not self._selected_binding_id:
            return
        label = self.recip_name_input.text().strip()
        email = self.recip_email_input.text().strip()
        output_dir = self.recip_dir_input.text().strip()

        if not label:
            QMessageBox.warning(self, "提示", "名称不能为空")
            return

        self._bm.update_binding_label(self._selected_binding_id, label)
        self._bm.update_binding_email(self._selected_binding_id, email)
        self._bm.update_binding_output_dir(self._selected_binding_id, output_dir)

        # Save custom SMTP if toggled
        if self.recip_smtp_check.isChecked():
            sender = self.recip_smtp_sender.text().strip()
            host = self.recip_smtp_host.text().strip()
            port = self.recip_smtp_port.value()
            pwd = self.recip_smtp_password.text().strip()
            self._bm.update_binding_smtp(self._selected_binding_id, sender, host, port)
            if pwd:
                self._cm.set_secret(
                    f"feishu.smtp_passwords.{self._selected_binding_id}", pwd
                )
                self.recip_smtp_password.clear()
                self.recip_smtp_password.setPlaceholderText("已保存（不显示）")
        else:
            self._bm.update_binding_smtp(self._selected_binding_id, "", "", 465)
            self._cm.delete_secret(
                f"feishu.smtp_passwords.{self._selected_binding_id}"
            )

        self._refresh_recipient_list()
        QMessageBox.information(self, "保存成功", f"接收人 '{label}' 已更新")

    def _add_recipient(self):
        from .binding_dialog import BindingDialog
        dlg = BindingDialog(self)
        dlg.binding_added.connect(self._on_recipient_added)
        dlg.exec()

    def _on_recipient_added(self, label, app_id, app_secret, open_id, email=""):
        try:
            self._bm.add_binding(label, app_id, app_secret, open_id, email=email)
            self._selected_binding_id = self._bm.get_active_binding_id()
            self._refresh_recipient_list()
        except ValueError as e:
            QMessageBox.warning(self, "绑定失败", str(e))

    def _delete_recipient(self):
        item = self.recipient_list.currentItem()
        if item is None:
            return
        binding_id = item.data(Qt.UserRole)
        if not binding_id:
            return
        binding = self._bm.get_binding_by_id(binding_id)
        label = binding["label"] if binding else "未知"
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除接收人 '{label}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._bm.remove_binding(binding_id)
            self._selected_binding_id = ""
            self._refresh_recipient_list()

    def _rebind_feishu(self):
        if not self._selected_binding_id:
            QMessageBox.information(self, "提示", "请先选择一个接收人")
            return
        from .binding_dialog import BindingDialog
        dlg = BindingDialog(self)
        dlg.binding_added.connect(self._on_rebind_done)
        dlg.exec()

    def _on_rebind_done(self, label, app_id, app_secret, open_id, email=""):
        if not self._selected_binding_id:
            return
        self._bm.update_binding_label(self._selected_binding_id, label)
        self._bm.update_binding_secret(self._selected_binding_id, app_secret)
        # Also update app_id and receive_id in the binding dict
        # Need a method for this — update the binding directly
        bindings = self._cm.get("feishu.bindings", [])
        for b in bindings:
            if b["id"] == self._selected_binding_id:
                b["app_id"] = app_id
                b["receive_id"] = open_id
                break
        self._cm.set("feishu.bindings", bindings)
        self._cm.save()
        if email:
            self._bm.update_binding_email(self._selected_binding_id, email)
        self._refresh_recipient_list()
        self._load_recipient_detail()
        QMessageBox.information(self, "成功", f"已重新绑定为 '{label}'")

    def _browse_recip_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择截图保存目录")
        if d:
            self.recip_dir_input.setText(d)

    # ── 截图 Tab ────────────────────────────────────────────────

    def _create_screenshot_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        group = QGroupBox("截图设置")
        form = QFormLayout()

        self.interval_combo = QComboBox()
        for m in INTERVAL_PRESETS:
            self.interval_combo.addItem(f"{m} 分钟", m)
        self.interval_combo.setEditable(True)
        form.addRow("间隔:", self.interval_combo)

        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setSuffix(" %")
        form.addRow("图片质量:", self.quality_spin)

        self.output_dir_input = QLineEdit()
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_global_dir)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.output_dir_input)
        dir_layout.addWidget(browse_btn)
        form.addRow("全局截图目录:", dir_layout)
        group.setLayout(form)
        layout.addWidget(group)

        clean_group = QGroupBox("自动清理")
        clean_form = QFormLayout()
        self.auto_clean_check = QCheckBox("启用自动清理")
        clean_form.addRow(self.auto_clean_check)
        self.retention_spin = QSpinBox()
        self.retention_spin.setRange(1, 365)
        self.retention_spin.setSuffix(" 天")
        clean_form.addRow("保留天数:", self.retention_spin)
        self.max_size_spin = QSpinBox()
        self.max_size_spin.setRange(1, 100)
        self.max_size_spin.setSuffix(" GB")
        clean_form.addRow("最大体积:", self.max_size_spin)
        clean_group.setLayout(clean_form)
        layout.addWidget(clean_group)

        layout.addStretch()
        return w

    def _browse_global_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择截图保存目录")
        if d:
            self.output_dir_input.setText(d)

    # ── 通用 Tab ────────────────────────────────────────────────

    def _create_general_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.auto_start_check = QCheckBox("开机自启动")
        layout.addWidget(self.auto_start_check)
        self.minimize_tray_check = QCheckBox("最小化到系统托盘")
        layout.addWidget(self.minimize_tray_check)
        self.keep_awake_check = QCheckBox("运行时阻止息屏")
        layout.addWidget(self.keep_awake_check)
        self.email_enabled_check = QCheckBox("启用邮件兜底推送")
        layout.addWidget(self.email_enabled_check)

        smtp_group = QGroupBox("SMTP 发件服务器（邮件兜底用）")
        smtp_form = QFormLayout()
        self.email_sender_input = QLineEdit()
        smtp_form.addRow("发件邮箱:", self.email_sender_input)
        self.email_password_input = QLineEdit()
        self.email_password_input.setEchoMode(QLineEdit.Password)
        smtp_form.addRow("密码/授权码:", self.email_password_input)
        self.smtp_host_input = QLineEdit()
        smtp_form.addRow("SMTP 服务器:", self.smtp_host_input)
        self.smtp_port_spin = QSpinBox()
        self.smtp_port_spin.setRange(1, 65535)
        smtp_form.addRow("端口:", self.smtp_port_spin)
        smtp_group.setLayout(smtp_form)
        layout.addWidget(smtp_group)

        layout.addStretch()
        return w

    # ── Load / Save ──────────────────────────────────────────────

    def _load_settings(self):
        # Screenshot
        interval = self._cm.get("screenshot.interval_minutes", 15)
        idx = self.interval_combo.findData(interval)
        if idx >= 0:
            self.interval_combo.setCurrentIndex(idx)
        else:
            self.interval_combo.setEditText(str(interval))
        self.quality_spin.setValue(self._cm.get("screenshot.quality", 80))
        self.output_dir_input.setText(self._cm.get("screenshot.output_dir", ""))

        self.auto_clean_check.setChecked(self._cm.get("storage.auto_clean", True))
        self.retention_spin.setValue(self._cm.get("storage.retention_days", 30))
        self.max_size_spin.setValue(self._cm.get("storage.max_size_gb", 5))

        # General
        self.auto_start_check.setChecked(self._cm.get("general.auto_start", False))
        self.minimize_tray_check.setChecked(self._cm.get("general.minimize_to_tray", True))
        self.keep_awake_check.setChecked(self._cm.get("general.keep_awake", True))

        # Email / SMTP
        self.email_enabled_check.setChecked(self._cm.get("email.enabled", False))
        self.email_sender_input.setText(self._cm.get("email.sender", ""))
        self.smtp_host_input.setText(self._cm.get("email.smtp_host", ""))
        self.smtp_port_spin.setValue(self._cm.get("email.smtp_port", 465))

        saved_pwd = self._cm.get_secret("email.password", "")
        self.email_password_input.setPlaceholderText(
            "已保存（不显示）" if saved_pwd else "输入授权码"
        )

    def _save(self):
        # Screenshot
        interval_text = self.interval_combo.currentText().replace(" 分钟", "").strip()
        try:
            interval = int(interval_text)
        except ValueError:
            interval = self.interval_combo.currentData() or 15
        self._cm.set("screenshot.interval_minutes", interval)
        self._cm.set("screenshot.quality", self.quality_spin.value())
        self._cm.set("screenshot.output_dir", self.output_dir_input.text())

        self._cm.set("storage.auto_clean", self.auto_clean_check.isChecked())
        self._cm.set("storage.retention_days", self.retention_spin.value())
        self._cm.set("storage.max_size_gb", self.max_size_spin.value())

        # General
        self._cm.set("general.auto_start", self.auto_start_check.isChecked())
        self._cm.set("general.minimize_to_tray", self.minimize_tray_check.isChecked())
        self._cm.set("general.keep_awake", self.keep_awake_check.isChecked())

        # Email / SMTP
        self._cm.set("email.enabled", self.email_enabled_check.isChecked())
        self._cm.set("email.sender", self.email_sender_input.text())
        self._cm.set("email.smtp_host", self.smtp_host_input.text())
        self._cm.set("email.smtp_port", self.smtp_port_spin.value())

        pwd = self.email_password_input.text().strip()
        if pwd:
            self._cm.set_secret("email.password", pwd)

        self._cm.save()
        QMessageBox.information(self, "保存成功", "设置已保存")
        self.accept()
