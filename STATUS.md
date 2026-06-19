# Screenshot Courier — 当前状态与问题清单

## 项目概述

定时截图实验电脑屏幕，通过飞书推送（主）或邮件（兜底）发送给用户，让研究人员无需守在仪器旁。

## 启动命令

```bash
cd "D:/Github_repository/Screenshot courier"
python run.py
```

依赖已安装（PySide6 降级到 6.7.0，因为 6.11.1 在 Anaconda 下 DLL 加载失败）。

## 项目结构

```
Screenshot Courier/
├── run.py                          # 启动入口
├── requirements.txt                # 依赖清单
├── resources/icon.ico              # 应用图标（已生成）
├── pic/                            # 截图存储目录
├── scripts/generate_icon.py        # 图标生成脚本
├── src/
│   ├── main.py                     # 初始化 QApplication + 显示主窗口
│   ├── config/
│   │   └── config_manager.py       # config.json 读写 + secrets.dat DPAPI 加密
│   ├── core/
│   │   ├── screenshot_engine.py    # MSS 截图
│   │   ├── scheduler.py            # APScheduler 定时调度
│   │   ├── storage.py              # 本地存档 + 自动清理（30天/5GB）
│   │   └── keep_awake.py           # SetThreadExecutionState 阻止息屏
│   ├── binding/
│   │   └── binding_manager.py      # 多绑定管理（增删切换，上限10个）
│   ├── notification/
│   │   ├── feishu_client.py        # 飞书图片上传 + 消息发送
│   │   ├── email_client.py         # yagmail SMTP 发送
│   │   ├── wecom_client.py         # 企业微信 webhook（Plan B）
│   │   └── notification_manager.py # 推送编排（重试3次 + 邮件兜底）
│   └── gui/
│       ├── main_window.py          # 主窗口控制面板
│       ├── tray_icon.py            # 系统托盘图标 + 右键菜单
│       ├── settings_dialog.py      # 设置对话框（截图/飞书/邮件/通用）
│       └── binding_dialog.py       # 飞书扫码绑定对话框
└── STATUS.md                       # 本文件
```

## 配置文件位置

- `C:\Users\<用户名>\AppData\Roaming\ScreenshotCourier\config.json` — 明文配置
- `C:\Users\<用户名>\AppData\Roaming\ScreenshotCourier\secrets.dat` — DPAPI 加密的密钥
- `C:\Users\<用户名>\AppData\Roaming\ScreenshotCourier\logs\screenshot_courier.log` — 日志
- `D:\Github_repository\Screenshot courier\pic\` — 截图存储

## 已实现的功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 定时截图 | ✅ | MSS 截主屏，JPEG 可调质量 |
| 本地存档 | ✅ | 按时间命名，自动清理 |
| 阻止息屏 | ✅ | SetThreadExecutionState |
| 多绑定管理 | ✅ | 上限10个，快速切换 |
| 系统托盘 | ✅ | 状态色标 + 右键菜单 |
| 主窗口 GUI | ✅ | 控制面板，显示状态/间隔/操作按钮 |
| 设置界面 | ✅ | 4个 Tab |
| 邮件兜底 | ⚠️ | 代码完成，未实测 |
| 企业微信 Plan B | ⚠️ | 代码完成，未实测 |
| 截图间隔持久化 | ✅ | config.json 保存 |
| 启动立即发图 | ✅ | 后台线程，不阻塞 UI |
| 邮箱与绑定关联 | ✅ | 每个接收人可关联独立邮箱 |

## 已修复的问题（2026-06-19）

### 修复 1：`config_manager.py` — logger 在定义前使用（严重）

**问题**：`except ImportError` 块（第 15 行）引用了 `logger`，但 `logger = logging.getLogger(__name__)` 在第 17 行才定义。如果 pywin32 未安装会直接 `NameError` 崩溃。

**修复**：将 `logger = logging.getLogger(__name__)` 移到 `try/except ImportError` 之前。

### 修复 2：`config_manager.py` — secrets.dat 解密不兼容

**问题**：旧版代码使用错误的 `CryptProtectData` 参数（第 5 参为 `0` 而非 `None`），导致已加密的 secrets.dat 无法被当前代码解密。

**修复**：新增 `_try_decrypt_secrets()` 方法，依次尝试 4 种参数组合回退解密（包括旧版的 `flags=0`、`description=""` 等常见变体）。若全部失败则给出明确的删除旧文件提示。

> **如果仍有解密失败**：手动删除 `%APPDATA%\ScreenshotCourier\secrets.dat`，然后重新绑定飞书接收人。

### 修复 3：`binding_dialog.py` — registerApp 失败时错误信息不足

**问题**：扫码绑定失败时只返回"未获取到应用凭证"，不指引用户下一步操作；且 `result` 可能不是 dict 导致 `.get()` 崩溃。

**修复**：
- 增加 `isinstance(result, dict)` 类型检查
- 失败时提示具体可能原因（取消、SDK 兼容、创建限制）
- 明确建议备选方案：在飞书开放平台手动创建应用 → 高级设置 → 手动配置
- 记录 `result` 的 keys 到日志辅助排错

### 修复 4：`generate_icon.py` — libpng iCCP 警告

**问题**：`resources/icon.ico` 中的 PNG 子图包含非标准 sRGB profile，Qt 加载时打印 libpng 警告。

**修复**：保存前执行 `img.info.pop("icc_profile", None)` 移除 ICC profile，重新运行脚本生成干净图标。

## 剩余需用户操作的事项

1. **如果 secrets.dat 解密仍失败**：删除 `%APPDATA%\ScreenshotCourier\secrets.dat`，重新绑定飞书
2. **验证飞书推送**：启动监控 → 查看日志 → 确认 `Image sent via Feishu` 是否出现
3. **配置邮件兜底**：高级设置 → 邮件 Tab → 填写 SMTP 信息 → 勾选启用
4. **飞书扫码失败时**：在 open.feishu.cn 手动创建应用，用高级设置中的手动配置填入凭证
