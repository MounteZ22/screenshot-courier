"""Main window — control panel GUI for Screenshot Courier."""

import logging
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QComboBox, QMessageBox, QFrame,
)
from PySide6.QtCore import QTimer, Signal, Slot, Qt
from PySide6.QtGui import QFont

from ..config.config_manager import ConfigManager
from ..binding.binding_manager import BindingManager
from ..core.screenshot_engine import capture_screen
from ..core.storage import build_shot_filename, get_output_dir, cleanup_old_screenshots
from ..core.keep_awake import keep_awake_on, keep_awake_off
from ..core.scheduler import create_scheduler, update_scheduler_interval
from ..notification.notification_manager import NotificationManager
from .tray_icon import TrayIcon
from .settings_dialog import SettingsDialog
from .binding_dialog import BindingDialog

logger = logging.getLogger(__name__)

INTERVAL_PRESETS = [5, 10, 15, 20, 30, 45, 60]


class MainWindow(QMainWindow):
    """Main window — control panel for monitoring."""

    _sig_update_status = Signal(bool, str)
    _sig_alert = Signal(str, str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screenshot Courier — 实验屏幕监控")
        self.setMinimumSize(480, 420)

        # Core services
        self._cm = ConfigManager()
        self._bm = BindingManager(self._cm)
        self._nm = NotificationManager(self._cm, self._bm)

        # State
        self._scheduler = None
        self._running = False
        self._output_dir = get_output_dir(self._cm.get("screenshot.output_dir", ""))
        self._keep_awake_enabled = self._cm.get("general.keep_awake", True)

        # Build UI
        self._build_ui()

        # Tray icon
        self._tray = TrayIcon(self._bm)
        self._tray.toggle_monitoring.connect(self._toggle_monitoring)
        self._tray.open_main_window.connect(self._show_main_window)
        self._tray.open_settings.connect(self._open_settings)
        self._tray.open_screenshot_dir.connect(self._open_screenshot_dir)
        self._tray.take_screenshot_now.connect(self._take_screenshot_now)
        self._tray.switch_binding.connect(self._switch_binding)
        self._tray.add_binding.connect(self._add_binding)
        self._tray.quit_app.connect(self._quit)

        # Thread-safe signals
        self._sig_update_status.connect(self._on_update_status)
        self._sig_alert.connect(self._tray.show_message)
        self._nm.set_alert_callback(lambda msg, lvl: self._sig_alert.emit("Screenshot Courier", msg, lvl))

        # Show tray
        self._tray.show()
        self._update_all()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # --- Header ---
        title = QLabel("Screenshot Courier")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("定时截图 + 自动推送，远程查看实验屏幕")
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # --- Status group ---
        status_group = QGroupBox("当前状态")
        sg_layout = QVBoxLayout(status_group)

        self._status_label = QLabel("● 已停止")
        self._status_label.setFont(QFont("Microsoft YaHei", 12))
        sg_layout.addWidget(self._status_label)

        recipient_row = QHBoxLayout()
        recipient_row.addWidget(QLabel("接收人:"))
        self._recipient_combo = QComboBox()
        self._recipient_combo.setMinimumWidth(150)
        self._recipient_combo.currentIndexChanged.connect(self._on_recipient_changed)
        recipient_row.addWidget(self._recipient_combo, 1)
        sg_layout.addLayout(recipient_row)

        self._interval_label = QLabel("间隔: 15 分钟")
        sg_layout.addWidget(self._interval_label)

        self._dir_label = QLabel(f"截图目录: {self._output_dir}")
        self._dir_label.setWordWrap(True)
        sg_layout.addWidget(self._dir_label)

        layout.addWidget(status_group)

        # --- Quick settings ---
        settings_row = QHBoxLayout()

        settings_row.addWidget(QLabel("截图间隔:"))
        self._interval_combo = QComboBox()
        for m in INTERVAL_PRESETS:
            self._interval_combo.addItem(f"{m} 分钟", m)
        self._interval_combo.setEditable(True)
        saved_interval = self._cm.get("screenshot.interval_minutes", 15)
        idx = self._interval_combo.findData(saved_interval)
        if idx >= 0:
            self._interval_combo.setCurrentIndex(idx)
        else:
            self._interval_combo.setEditText(str(saved_interval))
        self._interval_combo.currentIndexChanged.connect(self._on_interval_changed)
        settings_row.addWidget(self._interval_combo)

        layout.addLayout(settings_row)

        # --- Action buttons ---
        btn_layout = QHBoxLayout()

        self._start_btn = QPushButton("▶  开始监控")
        self._start_btn.setMinimumHeight(40)
        self._start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; color: white; border: none;
                border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        self._start_btn.clicked.connect(self._toggle_monitoring)
        btn_layout.addWidget(self._start_btn)

        self._now_btn = QPushButton("📸  立即截图")
        self._now_btn.setMinimumHeight(40)
        self._now_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; color: white; border: none;
                border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self._now_btn.clicked.connect(self._take_screenshot_now)
        btn_layout.addWidget(self._now_btn)

        layout.addLayout(btn_layout)

        # --- Bottom buttons ---
        bottom_layout = QHBoxLayout()

        bind_btn = QPushButton("新增接收人")
        bind_btn.clicked.connect(self._add_binding)
        bottom_layout.addWidget(bind_btn)

        settings_btn = QPushButton("高级设置")
        settings_btn.clicked.connect(self._open_settings)
        bottom_layout.addWidget(settings_btn)

        dir_btn = QPushButton("打开截图目录")
        dir_btn.clicked.connect(self._open_screenshot_dir)
        bottom_layout.addWidget(dir_btn)

        layout.addLayout(bottom_layout)

        layout.addStretch()

    def _show_main_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _update_all(self):
        """Refresh all UI state."""
        # Refresh recipient combo
        self._recipient_combo.blockSignals(True)
        self._recipient_combo.clear()
        bindings = self._bm.list_bindings()
        active_id = self._bm.get_active_binding_id()
        active_label = "未设置"
        selected_idx = -1
        for b in bindings:
            display = b["label"] + (f" ({b['email']})" if b.get("email") else "")
            self._recipient_combo.addItem(display, b["id"])
            if b["id"] == active_id:
                selected_idx = self._recipient_combo.count() - 1
                active_label = b["label"]
        if not bindings:
            self._recipient_combo.addItem("（无接收人，请先新增）", None)
        if selected_idx >= 0:
            self._recipient_combo.setCurrentIndex(selected_idx)
        self._recipient_combo.blockSignals(False)

        self._tray.update_recipient(active_label)

        interval = self._cm.get("screenshot.interval_minutes", 15)
        self._interval_label.setText(f"间隔: {interval} 分钟")
        self._dir_label.setText(f"截图目录: {self._output_dir}")

        self._update_status_ui()

    def _on_recipient_changed(self):
        binding_id = self._recipient_combo.currentData()
        if binding_id:
            self._bm.switch_binding(binding_id)
            self._tray.update_recipient(self._recipient_combo.currentText())

    def _update_status_ui(self):
        if self._running:
            self._status_label.setText("● 运行中")
            self._status_label.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
            self._start_btn.setText("⏸  暂停监控")
            self._start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800; color: white; border: none;
                    border-radius: 6px; font-size: 14px; font-weight: bold;
                }
                QPushButton:hover { background-color: #F57C00; }
            """)
        else:
            self._status_label.setText("● 已停止")
            self._status_label.setStyleSheet("color: #999; font-size: 14px; font-weight: bold;")
            self._start_btn.setText("▶  开始监控")
            self._start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50; color: white; border: none;
                    border-radius: 6px; font-size: 14px; font-weight: bold;
                }
                QPushButton:hover { background-color: #45a049; }
            """)

    def _on_interval_changed(self):
        data = self._interval_combo.currentData()
        if data is not None:
            interval = int(data)
        else:
            text = self._interval_combo.currentText().replace(" 分钟", "").strip()
            try:
                interval = int(text)
            except ValueError:
                return
        self._cm.set("screenshot.interval_minutes", interval)
        self._cm.save()
        self._interval_label.setText(f"间隔: {interval} 分钟")

        # Live-update scheduler if running
        if self._running and self._scheduler:
            update_scheduler_interval(self._scheduler, interval, self._do_screenshot_job)

    def _start_monitoring(self):
        if self._running:
            return
        if not self._bm.get_active_binding():
            QMessageBox.warning(self, "提示", "请先绑定至少一个飞书接收人")
            return

        interval = self._cm.get("screenshot.interval_minutes", 15)
        self._scheduler = create_scheduler(interval, self._do_screenshot_job)
        self._running = True

        if self._keep_awake_enabled:
            keep_awake_on()

        self._tray.update_status(True)
        self._update_status_ui()
        self._tray.show_message("Screenshot Courier", f"已开始监控（间隔 {interval} 分钟）", "info")
        logger.info("Monitoring started")

        # Immediately take the first screenshot in background thread
        QTimer.singleShot(500, self._run_screenshot_in_thread)

    def _stop_monitoring(self):
        if not self._running:
            return
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        self._running = False
        if self._keep_awake_enabled:
            keep_awake_off()
        self._tray.update_status(False)
        self._update_status_ui()
        logger.info("Monitoring stopped")

    def _toggle_monitoring(self):
        if self._running:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    @Slot(bool, str)
    def _on_update_status(self, running: bool, status: str):
        self._tray.update_status(running, status)
        self._update_status_ui()

    def _do_screenshot_job(self):
        try:
            filename = build_shot_filename()
            filepath = self._output_dir / filename
            capture_screen(filepath, quality=self._cm.get("screenshot.quality", 80))
            logger.info("Screenshot captured: %s", filepath)
            self._nm.send_screenshot(filepath)
            cleanup_old_screenshots(
                self._output_dir,
                retention_days=self._cm.get("storage.retention_days", 30),
                max_size_gb=self._cm.get("storage.max_size_gb", 5),
                auto_clean=self._cm.get("storage.auto_clean", True),
            )
            self._sig_update_status.emit(True, "normal")
        except Exception as e:
            logger.error("Screenshot job failed: %s", e, exc_info=True)
            self._sig_update_status.emit(True, "error")

    def _run_screenshot_in_thread(self):
        threading.Thread(target=self._do_screenshot_job, daemon=True).start()

    def _take_screenshot_now(self):
        if not self._bm.get_active_binding():
            QMessageBox.warning(self, "提示", "请先绑定接收人")
            return
        self._run_screenshot_in_thread()

    def _open_settings(self):
        dlg = SettingsDialog(self._cm, self._bm, self)
        dlg.exec()
        # Always refresh — bindings changes in settings take effect immediately
        self._output_dir = get_output_dir(self._cm.get("screenshot.output_dir", ""))
        self._keep_awake_enabled = self._cm.get("general.keep_awake", True)
        self._update_all()

    def _open_screenshot_dir(self):
        path = str(self._output_dir)
        if os.path.exists(path):
            subprocess.Popen(["explorer", path])

    def _switch_binding(self, binding_id: str):
        if self._bm.switch_binding(binding_id):
            self._update_all()

    def _add_binding(self):
        dlg = BindingDialog(self)
        dlg.binding_added.connect(self._on_new_binding)
        dlg.exec()

    def _on_new_binding(self, label, app_id, app_secret, open_id, email=""):
        try:
            self._bm.add_binding(label, app_id, app_secret, open_id, email=email)
            self._update_all()
            self._tray.show_message("Screenshot Courier", f"已添加接收人: {label}", "info")
        except ValueError as e:
            self._tray.show_message("绑定失败", str(e), "error")

    def _quit(self):
        self._stop_monitoring()
        self._tray.hide()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event):
        if self._cm.get("general.minimize_to_tray", True):
            event.ignore()
            self.hide()
            self._tray.show_message("Screenshot Courier", "已最小化到系统托盘", "info")
        else:
            self._quit()
