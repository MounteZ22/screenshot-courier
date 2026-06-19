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
)

from ..config.config_manager import ConfigManager
from ..binding.binding_manager import BindingManager

logger = logging.getLogger(__name__)

INTERVAL_PRESETS = [5, 10, 15, 20, 30, 45, 60]


class SettingsDialog(QDialog):
    """Settings dialog with tabs for different config sections."""

    def __init__(self, config_manager: ConfigManager, binding_manager: BindingManager, parent=None):
        super().__init__(parent)
        self._cm = config_manager
        self._bm = binding_manager
        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._create_screenshot_tab(), "截图")
        tabs.addTab(self._create_feishu_tab(), "飞书")
        tabs.addTab(self._create_email_tab(), "邮件")
        tabs.addTab(self._create_general_tab(), "通用")
        layout.addWidget(tabs)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _create_screenshot_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        # Interval
        group = QGroupBox("截图间隔")
        form = QFormLayout()
        self.interval_combo = QComboBox()
        for m in INTERVAL_PRESETS:
            self.interval_combo.addItem(f"{m} 分钟", m)
        self.interval_combo.setEditable(True)
        form.addRow("预设间隔:", self.interval_combo)

        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setSuffix(" %")
        form.addRow("图片质量:", self.quality_spin)

        self.output_dir_input = QLineEdit()
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_output_dir)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.output_dir_input)
        dir_layout.addWidget(browse_btn)
        form.addRow("保存目录:", dir_layout)
        group.setLayout(form)
        layout.addWidget(group)

        # Storage cleanup
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

    def _create_feishu_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.feishu_enabled_check = QCheckBox("启用飞书推送")
        layout.addWidget(self.feishu_enabled_check)

        # Binding list
        group = QGroupBox("接收人列表")
        group_layout = QVBoxLayout()
        self.binding_list_widget = QListWidget()
        self.binding_list_widget.setMaximumHeight(120)
        self._refresh_binding_list()
        self.binding_list_widget.itemDoubleClicked.connect(self._switch_to_binding)
        group_layout.addWidget(self.binding_list_widget)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("新增绑定...")
        add_btn.clicked.connect(self._add_binding)
        switch_btn = QPushButton("切换到此")
        switch_btn.clicked.connect(lambda: self._switch_to_binding(self.binding_list_widget.currentItem()))
        remove_btn = QPushButton("删除选中")
        remove_btn.clicked.connect(self._remove_binding)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(switch_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        group_layout.addLayout(btn_layout)
        group.setLayout(group_layout)
        layout.addWidget(group)

        # Edit active binding's email
        email_group = QGroupBox("当前接收人邮箱（飞书失败时邮件通知）")
        email_form = QFormLayout()
        self.binding_email_input = QLineEdit()
        self.binding_email_input.setPlaceholderText("选填，如 zhangsan@example.com")
        save_email_btn = QPushButton("保存邮箱")
        save_email_btn.clicked.connect(self._save_binding_email)
        email_layout = QHBoxLayout()
        email_layout.addWidget(self.binding_email_input)
        email_layout.addWidget(save_email_btn)
        email_form.addRow("备用邮箱:", email_layout)
        email_group.setLayout(email_form)
        layout.addWidget(email_group)

        # Update secret for existing binding
        update_group = QGroupBox("补充密钥（已有绑定丢失 secret 时使用）")
        update_form = QFormLayout()
        hint_label = QLabel("如果 secrets.dat 丢失，可在飞书开放平台后台查到 app_secret 填入，无需重新扫码。")
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #666; font-size: 11px;")
        update_form.addRow(hint_label)
        self.update_binding_combo = QComboBox()
        update_form.addRow("选择接收人:", self.update_binding_combo)
        self.update_secret_input = QLineEdit()
        self.update_secret_input.setEchoMode(QLineEdit.Password)
        self.update_secret_input.setPlaceholderText("填入 app_secret")
        update_form.addRow("App Secret:", self.update_secret_input)
        update_btn = QPushButton("更新密钥")
        update_btn.clicked.connect(self._update_binding_secret)
        update_form.addRow("", update_btn)
        update_group.setLayout(update_form)
        layout.addWidget(update_group)

        # Manual app config (fallback)
        manual_group = QGroupBox("手动新增绑定（扫码失败时使用）")
        manual_form = QFormLayout()
        self.app_id_input = QLineEdit()
        self.app_id_input.setPlaceholderText("cli_xxxxxxxxx")
        manual_form.addRow("App ID:", self.app_id_input)
        self.app_secret_input = QLineEdit()
        self.app_secret_input.setEchoMode(QLineEdit.Password)
        manual_form.addRow("App Secret:", self.app_secret_input)
        self.open_id_input = QLineEdit()
        self.open_id_input.setPlaceholderText("ou_xxxxxxxxx")
        manual_form.addRow("Open ID:", self.open_id_input)
        manual_save_btn = QPushButton("保存为新绑定")
        manual_save_btn.clicked.connect(self._save_manual_binding)
        manual_form.addRow("", manual_save_btn)
        manual_group.setLayout(manual_form)
        layout.addWidget(manual_group)

        layout.addStretch()
        return w

    def _create_email_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.email_enabled_check = QCheckBox("启用邮件推送（兜底）")
        layout.addWidget(self.email_enabled_check)

        # Per-binding email hint
        hint = QLabel("提示：每个接收人可关联独立邮箱。切换接收人时自动切换收件邮箱。\n"
                       "下方填写的[收件邮箱]作为全局默认，绑定中设置的邮箱优先。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(hint)

        group = QGroupBox("SMTP 配置")
        form = QFormLayout()
        self.email_sender_input = QLineEdit()
        form.addRow("发件邮箱:", self.email_sender_input)
        self.email_password_input = QLineEdit()
        self.email_password_input.setEchoMode(QLineEdit.Password)
        form.addRow("密码/授权码:", self.email_password_input)
        self.smtp_host_input = QLineEdit()
        form.addRow("SMTP 服务器:", self.smtp_host_input)
        self.smtp_port_spin = QSpinBox()
        self.smtp_port_spin.setRange(1, 65535)
        form.addRow("端口:", self.smtp_port_spin)
        self.email_recipient_input = QLineEdit()
        form.addRow("收件邮箱:", self.email_recipient_input)
        group.setLayout(form)
        layout.addWidget(group)

        layout.addStretch()
        return w

    def _create_general_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.auto_start_check = QCheckBox("开机自启动")
        layout.addWidget(self.auto_start_check)
        self.minimize_tray_check = QCheckBox("最小化到系统托盘")
        layout.addWidget(self.minimize_tray_check)
        self.keep_awake_check = QCheckBox("运行时阻止息屏")
        layout.addWidget(self.keep_awake_check)

        layout.addStretch()
        return w

    def _browse_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择截图保存目录")
        if d:
            self.output_dir_input.setText(d)

    def _refresh_binding_list(self):
        bindings = self._bm.list_bindings()
        active_id = self._bm.get_active_binding_id()

        # Refresh list widget
        self.binding_list_widget.clear()
        if not bindings:
            self.binding_list_widget.addItem("（暂无绑定）")
        else:
            for b in bindings:
                marker = "▶ " if b["id"] == active_id else "  "
                email_hint = f" | 邮箱: {b['email']}" if b.get("email") else ""
                text = f"{marker}{b['label']}{email_hint}  (创建于 {b.get('created_at', '')[:10]})"
                item = QListWidgetItem(text)
                item.setData(1, b["id"])
                self.binding_list_widget.addItem(item)

        # Refresh update-secret combo (may not exist yet on first call)
        if hasattr(self, "update_binding_combo"):
            self.update_binding_combo.clear()
            for b in bindings:
                self.update_binding_combo.addItem(b["label"], b["id"])

    def _switch_to_binding(self, item):
        if item is None:
            return
        binding_id = item.data(1)
        if binding_id and self._bm.switch_binding(binding_id):
            self._refresh_binding_list()

    def _remove_binding(self):
        item = self.binding_list_widget.currentItem()
        if item is None:
            QMessageBox.information(self, "提示", "请先在列表中选择一个接收人")
            return
        binding_id = item.data(1)
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
            self._refresh_binding_list()

    def _add_binding(self):
        from .binding_dialog import BindingDialog
        dlg = BindingDialog(self)
        dlg.binding_added.connect(self._on_binding_added)
        dlg.exec()

    def _on_binding_added(self, label, app_id, app_secret, open_id, email=""):
        try:
            self._bm.add_binding(label, app_id, app_secret, open_id, email=email)
            self._refresh_binding_list()
        except ValueError as e:
            QMessageBox.warning(self, "绑定失败", str(e))

    def _update_binding_secret(self):
        binding_id = self.update_binding_combo.currentData()
        if not binding_id:
            QMessageBox.information(self, "提示", "请先选择接收人")
            return
        secret = self.update_secret_input.text().strip()
        if not secret:
            QMessageBox.warning(self, "提示", "请输入 App Secret")
            return
        if self._bm.update_binding_secret(binding_id, secret):
            QMessageBox.information(self, "成功", "密钥已更新")
            self.update_secret_input.clear()

    def _save_binding_email(self):
        """Save email for the currently active binding."""
        active_id = self._bm.get_active_binding_id()
        if not active_id:
            QMessageBox.warning(self, "提示", "请先添加一个接收人")
            return
        email = self.binding_email_input.text().strip()
        self._bm.update_binding_email(active_id, email)
        self._refresh_binding_list()
        QMessageBox.information(self, "保存成功", f"已为当前接收人设置备用邮箱" if email else "已清除当前接收人的备用邮箱")

    def _save_manual_binding(self):
        app_id = self.app_id_input.text().strip()
        app_secret = self.app_secret_input.text().strip()
        open_id = self.open_id_input.text().strip()
        if not all([app_id, app_secret, open_id]):
            QMessageBox.warning(self, "提示", "请填写完整的 App ID、App Secret 和 Open ID")
            return
        label = app_id  # use app_id as label if no better name
        try:
            self._bm.add_binding(label, app_id, app_secret, open_id)
            self._refresh_binding_list()
            QMessageBox.information(self, "成功", f"绑定已保存（标签: {label}）")
            self.app_id_input.clear()
            self.app_secret_input.clear()
            self.open_id_input.clear()
        except ValueError as e:
            QMessageBox.warning(self, "绑定失败", str(e))

    def _load_settings(self):
        """Load current settings into UI."""
        # Screenshot
        interval = self._cm.get("screenshot.interval_minutes", 15)
        idx = self.interval_combo.findData(interval)
        if idx >= 0:
            self.interval_combo.setCurrentIndex(idx)
        else:
            self.interval_combo.setEditText(str(interval))
        self.quality_spin.setValue(self._cm.get("screenshot.quality", 80))
        self.output_dir_input.setText(self._cm.get("screenshot.output_dir", ""))

        # Storage
        self.auto_clean_check.setChecked(self._cm.get("storage.auto_clean", True))
        self.retention_spin.setValue(self._cm.get("storage.retention_days", 30))
        self.max_size_spin.setValue(self._cm.get("storage.max_size_gb", 5))

        # Feishu
        self.feishu_enabled_check.setChecked(self._cm.get("feishu.enabled", True))

        # Load active binding's email
        active = self._bm.get_active_binding()
        if active:
            self.binding_email_input.setText(active.get("email", ""))

        # Email
        self.email_enabled_check.setChecked(self._cm.get("email.enabled", False))
        self.email_sender_input.setText(self._cm.get("email.sender", ""))
        self.smtp_host_input.setText(self._cm.get("email.smtp_host", ""))
        self.smtp_port_spin.setValue(self._cm.get("email.smtp_port", 465))
        self.email_recipient_input.setText(self._cm.get("email.recipient", ""))

        # General
        self.auto_start_check.setChecked(self._cm.get("general.auto_start", False))
        self.minimize_tray_check.setChecked(self._cm.get("general.minimize_to_tray", True))
        self.keep_awake_check.setChecked(self._cm.get("general.keep_awake", True))

    def _save(self):
        """Save settings from UI to config."""
        # Screenshot
        interval_text = self.interval_combo.currentText().replace(" 分钟", "").strip()
        try:
            interval = int(interval_text)
        except ValueError:
            interval = self.interval_combo.currentData() or 15
        self._cm.set("screenshot.interval_minutes", interval)
        self._cm.set("screenshot.quality", self.quality_spin.value())
        self._cm.set("screenshot.output_dir", self.output_dir_input.text())

        # Storage
        self._cm.set("storage.auto_clean", self.auto_clean_check.isChecked())
        self._cm.set("storage.retention_days", self.retention_spin.value())
        self._cm.set("storage.max_size_gb", self.max_size_spin.value())

        # Feishu
        self._cm.set("feishu.enabled", self.feishu_enabled_check.isChecked())

        # Email
        self._cm.set("email.enabled", self.email_enabled_check.isChecked())
        self._cm.set("email.sender", self.email_sender_input.text())
        self._cm.set("email.smtp_host", self.smtp_host_input.text())
        self._cm.set("email.smtp_port", self.smtp_port_spin.value())
        self._cm.set("email.recipient", self.email_recipient_input.text())

        # General
        self._cm.set("general.auto_start", self.auto_start_check.isChecked())
        self._cm.set("general.minimize_to_tray", self.minimize_tray_check.isChecked())
        self._cm.set("general.keep_awake", self.keep_awake_check.isChecked())

        # Save email password to secrets
        pwd = self.email_password_input.text().strip()
        if pwd:
            self._cm.set_secret("email.password", pwd)

        self._cm.save()
        QMessageBox.information(self, "保存成功", "设置已保存")
        self.accept()
