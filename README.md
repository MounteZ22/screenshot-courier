# Screenshot Courier

定时截取实验电脑屏幕，通过飞书机器人推送到手机上，让研究人员不用一直守在仪器旁。

## 功能

- **定时截图** — MSS 截主屏，JPEG 可调质量，间隔可设（1–60 分钟）
- **飞书推送** — 扫码绑定飞书机器人，截图直接发到飞书消息
- **多人管理** — 支持多接收人快速切换，每人可设独立截图目录
- **邮件兜底** — 飞书失败时自动通过邮件发送（支持每人自定义 SMTP）
- **本地存档** — 截图本地留存，支持按天数和体积自动清理
- **系统托盘** — 最小化到托盘，阻止息屏，右键快捷操作

## 安装

```bash
pip install -r requirements.txt
```

依赖：Python 3.10+，Windows（DPAPI 加密 + SetThreadExecutionState 阻止息屏）。

## 使用

```bash
python run.py
```

1. 打开「高级设置 → 接收人」→ 点击「新增」→ 扫码绑定飞书机器人，可顺便填兜底邮箱
2. 在首页下拉框选择接收人，设置间隔 → 点击「开始监控」
3. 截图会通过飞书发送到手机上；飞书失败时走邮件兜底（需在「通用」Tab 配置 SMTP）

## 数据存储

- `config.json`（明文）— app_id、接收人信息、邮箱、目录等
- `secrets.dat`（DPAPI 加密）— app_secret、SMTP 授权码，仅当前 Windows 用户可解密

两个文件都在 `%APPDATA%\ScreenshotCourier\` 下。
