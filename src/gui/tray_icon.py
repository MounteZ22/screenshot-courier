"""System tray icon with status and quick actions."""

import logging
from pathlib import Path

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtCore import Signal, QObject

from ..binding.binding_manager import BindingManager

logger = logging.getLogger(__name__)


def _create_color_icon(color: str, size: int = 32) -> QIcon:
    """Create a simple colored circle icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setBrush(QColor(color))
    painter.setPen(QColor(color))
    painter.drawEllipse(2, 2, size - 4, size - 4)
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QObject):
    """System tray icon with context menu for quick actions."""

    # Signals
    toggle_monitoring = Signal()  # pause/resume
    open_main_window = Signal()   # double-click
    open_settings = Signal()
    open_screenshot_dir = Signal()
    take_screenshot_now = Signal()
    switch_binding = Signal(str)  # binding_id
    add_binding = Signal()
    quit_app = Signal()

    def __init__(self, binding_manager: BindingManager, parent=None):
        super().__init__(parent)
        self._bm = binding_manager
        self._icon = QSystemTrayIcon()
        self._is_running = False
        self._setup_icon()
        self._build_menu()
        self._icon.activated.connect(self._on_activated)

    def _setup_icon(self):
        self._icon_green = _create_color_icon("#4CAF50")
        self._icon_yellow = _create_color_icon("#FF9800")
        self._icon_red = _create_color_icon("#F44336")
        self._icon_gray = _create_color_icon("#9E9E9E")
        self._icon.setIcon(self._icon_gray)
        self._icon.setToolTip("Screenshot Courier - 未运行")

    def _build_menu(self):
        menu = QMenu()

        # Current recipient display
        self._recipient_action = QAction("当前接收人: 未设置")
        self._recipient_action.setEnabled(False)
        menu.addAction(self._recipient_action)

        menu.addSeparator()

        # Switch recipient submenu
        self._switch_menu = menu.addMenu("切换接收人")
        self._refresh_switch_menu()

        menu.addSeparator()

        self._toggle_action = QAction("开始监控")
        self._toggle_action.triggered.connect(self.toggle_monitoring.emit)
        menu.addAction(self._toggle_action)

        take_now = QAction("立即截图")
        take_now.triggered.connect(self.take_screenshot_now.emit)
        menu.addAction(take_now)

        menu.addSeparator()

        open_dir = QAction("打开截图目录")
        open_dir.triggered.connect(self.open_screenshot_dir.emit)
        menu.addAction(open_dir)

        settings = QAction("打开设置")
        settings.triggered.connect(self.open_settings.emit)
        menu.addAction(settings)

        menu.addSeparator()

        quit_action = QAction("退出")
        quit_action.triggered.connect(self.quit_app.emit)
        menu.addAction(quit_action)

        self._menu = menu
        self._icon.setContextMenu(menu)

    def _refresh_switch_menu(self):
        """Rebuild the switch-recipient submenu."""
        self._switch_menu.clear()
        bindings = self._bm.list_bindings()
        active_id = self._bm.get_active_binding_id()

        for b in bindings:
            action = QAction(b["label"])
            action.setCheckable(True)
            action.setChecked(b["id"] == active_id)
            action.triggered.connect(lambda checked, bid=b["id"]: self.switch_binding.emit(bid))
            self._switch_menu.addAction(action)

        self._switch_menu.addSeparator()
        add_action = QAction("+ 新增绑定...")
        add_action.triggered.connect(self.add_binding.emit)
        self._switch_menu.addAction(add_action)

    def update_status(self, running: bool, status: str = "normal"):
        """Update tray icon and tooltip based on app state."""
        self._is_running = running
        if status == "error":
            self._icon.setIcon(self._icon_red)
            self._icon.setToolTip("Screenshot Courier - 异常")
        elif status == "warning":
            self._icon.setIcon(self._icon_yellow)
            self._icon.setToolTip("Screenshot Courier - 告警")
        elif running:
            self._icon.setIcon(self._icon_green)
            self._icon.setToolTip("Screenshot Courier - 运行中")
        else:
            self._icon.setIcon(self._icon_gray)
            self._icon.setToolTip("Screenshot Courier - 已暂停")

        self._toggle_action.setText("暂停监控" if running else "开始监控")

    def update_recipient(self, label: str):
        """Update the displayed current recipient."""
        self._recipient_action.setText(f"当前接收人: {label}")
        self._refresh_switch_menu()

    def show_message(self, title: str, message: str, level: str = "warning"):
        """Show a system tray notification."""
        icon_map = {
            "info": QSystemTrayIcon.MessageIcon.Information,
            "warning": QSystemTrayIcon.MessageIcon.Warning,
            "error": QSystemTrayIcon.MessageIcon.Critical,
        }
        self._icon.showMessage(title, message, icon_map.get(level, QSystemTrayIcon.MessageIcon.Warning), 5000)

    def show(self):
        self._icon.show()

    def hide(self):
        self._icon.hide()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_main_window.emit()
