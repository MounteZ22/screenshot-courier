# Screenshot Courier — 需求与设计方案 (v0.2)

> **版本说明**
> - v0.1(初稿):提出 iLink Bot API 作主推送通道
> - **v0.2(本版)**:基于评审反馈修订。主要变更:
>   1. 主推送通道由微信 iLink Bot API 改为**飞书(registerApp 扫码绑定)**
>   2. 新增**企业微信群机器人**作为 Plan B 备选方案
>   3. 明确为**固定机器人 + 默认私聊**模式,绑定持久化,日常不扫码
>   4. 支持**多绑定 + 快速切换**(一台仪器多人共用场景)
>   5. 新增**运行时阻止息屏**机制
>   6. **本地按时间存图**升级为核心默认行为 + 自动清理
>   7. 打包方式由 `--onefile` 改为 `--onedir` + 安装包
>   8. 推送失败改为**重试 3 次 + 告警 + 邮件兜底**,完整补发留作后续
>   9. 敏感信息用 DPAPI 加密
>   10. 删除多显示器选择(实验电脑均单屏,默认截主屏)

---

## 一、项目背景

### 1.1 问题描述

课题组同门在运行试验过程中,需要经常待在仪器和电脑附近,查看电脑记录传感器输出的数据。这限制了研究人员的活动范围,无法离开实验室去做其他工作。

### 1.2 核心需求

设计一个定时截图 + 自动推送工具,让用户可以远程查看实验电脑的屏幕状态,无需一直守在仪器旁边。

### 1.3 目标用户

- 生化环材专业研究人员
- 对计算机工程、软件工程相关知识了解有限
- 需要易安装、易使用、稳定可靠的工具

### 1.4 设计约束

1. **易安装部署** — 不需要复杂的环境配置,最好双击即运行
2. **易使用** — 界面直观,操作简单,不需要技术背景
3. **运行稳定** — 长时间运行不崩溃,有异常自动恢复机制
4. **不干扰实验** — 不影响仪器电脑的数据接收和记录,占用资源少

---

## 二、功能需求

### 2.1 核心功能

| 功能 | 描述 |
|------|------|
| 定时截图 | 按设定的时间间隔自动截取电脑屏幕 |
| 飞书推送 | 将截图通过飞书机器人发送给用户(主) |
| 邮件推送 | 将截图通过邮件发送(兜底) |
| 配置管理 | 可视化界面配置截图间隔、推送方式等 |
| 后台运行 | 最小化到系统托盘,不干扰其他工作 |
| 本地存档 | 所有截图按时间命名存到本地目录,可回溯 |
| 阻止息屏 | 软件运行期间自动阻止系统息屏/休眠 |

### 2.2 截图间隔

- 预设选项:5、10、15、20、30、45、60 分钟
- 用户可自定义任意间隔(分钟,最小 1 分钟)
- *(取消 v0.1 "必须 5 的倍数" 的限制,避免给非技术用户徒增困惑)*

### 2.3 推送模式(重要决策)

**固定机器人 + 默认私聊 + 多绑定切换**

- 用户**首次**扫码绑定一个飞书机器人(详见 3.2)
- 绑定关系**持久化到本地**,以后开机自动恢复,**无需每次扫码**
- 截图通过该机器人以**私聊**形式发给用户
- 高级选项:用户可改为发往一个**指定飞书群**(供课题组共用实验电脑场景)
- **支持多绑定**:一台仪器多人共用时,每人首次扫码存档,日常从托盘菜单**快速切换**接收人(见 2.3.2)
- **明确不采用** "每次实验扫码拉新群" 模式(见 2.3.1)

### 2.3.1 为什么不采用 "每次扫码拉新群"

`registerApp` 的语义是**创建一个飞书应用**,而非建群。若每次实验都调用:

- 单个飞书账号下应用数有上限(约 50 个),反复调用会触顶失效
- 每次都要重走权限授权流程,违背 "双击即用"
- 历史截图分散在几十个群里,无法回溯
- 建群天然涉及多人,与 "发给个人、不打扰课题组" 冲突

因此采用 **"建一次、长期用"** 的固定绑定模式,符合 `registerApp` 的设计本意,也与 Proma 等成熟产品一致。

### 2.3.2 多人共用仪器电脑:多绑定 + 快速切换

实验场景中,一台仪器电脑常被多人轮流使用(课题组轮班、师生交接)。若采用 "单人单绑定、换人解绑重扫",会反复触发 `registerApp`,导致每个用户的飞书账号下应用数量累积(单账号上限约 50 个),且每次重配权限体验差。

**方案:多绑定存档 + 快速切换**

- 每个用户在**该电脑首次使用**时扫码一次,绑定信息(姓名备注 + 凭证)存档到本地
- 日常使用时,从托盘右键菜单**一键切换**当前接收人,下一张截图立即发给新接收人
- 切换是**即时**的,不重新扫码、不重配权限、不堆积应用
- "新增绑定" 才触发扫码;已存档的接收人可随时删除

**托盘菜单示意:**

```
📸 当前接收人: 张三
─────────────
切换接收人 ▶   ✓ 张三
                李四
                王五
                ＋ 新增绑定...
─────────────
立即截图
暂停监控 | 打开设置 | 打开截图目录 | 退出
```

**单人专用电脑也完全兼容**:列表里只有一个人,永不切换,体验等同单绑定。因此本机制是单人/多人场景的统一方案。

**接收人存档上限**:为避免凭证文件膨胀,单台电脑最多保存 **10 个**绑定,超出提示删除旧的。

*(后续增强:可做成多选,同时发给多个接收人,供 "我和师姐一起盯这次实验" 场景。不列入首版。)*

### 2.4 推送机制

**主推送:飞书**
- 通过飞书官方 Lark SDK `registerApp` 扫码一键创建应用并绑定
- 基于 OAuth 2.0 Device Authorization Grant(RFC 8628),无需企业管理员审核
- 发送图片消息(上传拿 image_key → 发消息)

**兜底推送:邮件**
- 通过 SMTP 协议发送
- 触发条件:飞书重试 3 次仍失败,或绑定凭证失效
- 最通用、最稳定,几乎不会挂

**绑定失效处理**
- 凭证失效(如用户在飞书后台删了应用)时:
  1. 托盘图标变红 + 弹窗提示 "请重新扫码绑定"
  2. **同时**自动切到邮件兜底,不丢截图
- 既告知用户问题,又不中断监控

### 2.5 运行方式

- **系统托盘** — 最小化后在右下角显示小图标
- **状态可见** — 托盘图标显示运行状态(运行中 / 暂停 / 异常)
- **快速操作** — 右键菜单可暂停/继续、打开设置、立即截图、打开截图目录、查看日志

---

## 三、技术方案

### 3.1 技术栈选型

| 模块 | 技术方案 | 选择理由 |
|------|----------|----------|
| 截图引擎 | MSS | 高性能、跨平台、资源占用极低 |
| 定时调度 | APScheduler | 后台运行、灵活触发规则、支持持久化 |
| 飞书推送 | Lark Python SDK (`lark-oapi`) | 官方维护、支持 registerApp 扫码建应用 |
| 邮件推送 | yagmail / smtplib | 简洁 API、支持各种邮箱服务商 |
| GUI 界面 | PySide6 | 丰富组件、原生系统托盘支持、LGPL 友好 |
| 息屏阻止 | pywin32 (`SetThreadExecutionState`) | Windows 原生 API,几行代码 |
| 配置加密 | `win32crypt`(DPAPI)/ `keyring` | Windows 原生,对用户透明 |
| 打包工具 | PyInstaller(`--onedir`) + Inno Setup | 启动快、好升级、安装包体验 |

### 3.2 飞书推送方案详述(主通道)

#### 3.2.1 registerApp 扫码绑定机制

飞书官方 Lark SDK 提供 `registerApp` 方法,基于 **OAuth 2.0 Device Authorization Grant(RFC 8628)** 协议:

> 调用该方法会返回一个验证链接,用户在飞书或 Lark 中打开该链接(扫码)完成授权后,SDK 自动**注册一个应用**并返回凭证(`app_id` / `app_secret`)。

**关键优势:**
- 用户无需去飞书开放平台手动创建应用
- 无需企业管理员审核
- 拿到的应用凭证可长期使用

#### 3.2.2 绑定流程(多绑定版)

软件维护一个**绑定列表**,每个绑定对应一个飞书接收人。任一时刻有一个 "当前激活" 绑定,截图发给它。

```
新增绑定(每个新用户在该电脑首次使用时各做一次):
1. 用户在软件里点 "新增绑定" → 填姓名备注(如 "张三")
   ↓
2. 软件调用 registerApp,获得扫码链接,显示二维码
   ↓
3. 用户用自己手机飞书扫码确认
   ↓
4. SDK 返回 { app_id, app_secret, open_id }
   ↓
5. 软件把该绑定加密追加存到本地 bindings 列表,并设为当前激活
   ↓
6. 引导用户配置一次权限(一键复制 JSON + 跳转飞书后台)
   ↓
7. 该接收人绑定完成,后续在该电脑上无需再扫

日常使用(开机后,无需扫码):
1. 软件读 bindings 列表 + 当前激活标记
   ↓
2. 用激活绑定的 app_id/secret 换 tenant_access_token(2h 有效,自动续期)
   ↓
3. 截图发给激活绑定对应的 open_id
   ↓
4. 换人实验 → 托盘菜单切换激活绑定 → 下一张图发给新人

切换/删除绑定(日常,不扫码):
- 托盘 "切换接收人" → 选列表里另一人 → 立即生效
- 设置页 "删除绑定" → 移除某接收人(不影响其在飞书侧的应用)

需重新扫码的情况(罕见):
- 用户主动 "新增绑定"(新来的同门)
- 某绑定凭证失效(用户在飞书后台删了对应应用)
- 换电脑(本地 bindings 未迁移)
```

**关键原则:扫码只发生在 "新增绑定",切换/删除/日常都不扫。**

#### 3.2.3 飞书权限配置

扫码建好应用后,需要在飞书后台为该应用开启以下权限(Proma 经验:做成 "一键复制权限 JSON" 按钮降低摩擦):

| 权限 | 用途 |
|------|------|
| `im:message:send_as_bot` | 以机器人身份发消息 |
| `im:message` | 发送/读取消息 |
| `im:resource` | 上传/下载图片等资源 |
| `im:message.p2p_msg:readonly` | 私聊消息(如需双向) |
| `contact:user.base:readonly` | 解析用户身份 |

#### 3.2.4 发图片(两步走)

飞书发图片不同于企业微信群机器人的一步 POST,需要两步:

```python
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateImageRequest, CreateImageRequestBody,
    CreateMessageRequest, CreateMessageRequestBody,
)

def send_feishu_image(client, receive_id, image_path):
    """第 1 步:上传图片,拿 image_key"""
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    upload_req = CreateImageRequest.builder() \
        .request_body(CreateImageRequestBody.builder()
            .image_type("message")
            .image(lark.File(img_bytes, "shot.jpg"))
            .build()) \
        .build()
    upload_resp = client.im.v1.image.create(upload_req)
    if not upload_resp.success():
        raise RuntimeError(f"上传失败: {upload_resp.msg}")
    image_key = upload_resp.data.image_key

    """第 2 步:发消息引用 image_key(私聊 receive_id_type=open_id)"""
    import json
    msg_req = CreateMessageRequest.builder() \
        .receive_id_type("open_id") \
        .request_body(CreateMessageRequestBody.builder()
            .receive_id(receive_id)
            .msg_type("image")
            .content(json.dumps({"image_key": image_key}))
            .build()) \
        .build()
    msg_resp = client.im.v1.message.create(msg_req)
    if not msg_resp.success():
        raise RuntimeError(f"发送失败: {msg_resp.msg}")
    return msg_resp.data.message_id
```

#### 3.2.5 token 自动续期

- `tenant_access_token` 有效期 2 小时
- 封装一个 `FeishuClient` 类,内部记录过期时间,过期前 5 分钟自动重新换取
- 失败时抛异常,由上层 `NotificationManager` 触发重试/兜底逻辑

### 3.3 邮件推送方案详述(兜底通道)

```python
import yagmail

def send_email(image_path, to_email, smtp_cfg):
    """通过邮件发送截图(SMTP)"""
    yag = yagmail.SMTP(
        user=smtp_cfg['sender'],
        password=smtp_cfg['password'],
        host=smtp_cfg['smtp_host'],
        port=smtp_cfg.get('smtp_port', 465),
    )
    yag.send(
        to=to_email,
        subject=f'实验屏幕截图',
        contents='当前实验屏幕截图如下:',
        attachments=image_path,
    )
```

**支持的邮箱服务商:** QQ 邮箱、163 邮箱、Gmail、Outlook、企业邮箱

### 3.4 截图方案详述

```python
import mss
from PIL import Image

def capture_screen(output_path, quality=80):
    """截取主显示器并压缩保存为 JPEG"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # 主屏(实验电脑均单屏,不做选择)
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        img.save(output_path, "JPEG", quality=quality)
    return output_path
```

**性能特点**
- 截图速度:~60 FPS(远超需求,1-2 FPS 即可)
- 资源占用:极低,不会影响其他程序

### 3.5 本地存档方案(核心默认行为)

所有截图**先存本地,再推送**。这带来三重收益:

1. 推送失败也不丢数据(天然兜底)
2. 用户回实验室可翻历史,像回放
3. 出问题时可回溯 "3 点 15 分那张截图拍到啥了"

```python
from datetime import datetime

def build_shot_filename(now=None):
    """按时间命名:2026-06-19_141530.jpg"""
    now = now or datetime.now()
    return now.strftime("%Y-%m-%d_%H%M%S") + ".jpg"
```

**自动清理策略(防止硬盘塞满)**
- 默认:保留最近 **30 天** + 总大小不超过 **5 GB**,超出自动删最旧
- 用户可在设置里调整天数 / 体积阈值 / 关闭清理

### 3.6 定时调度方案

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

def start_scheduler(interval_minutes, job_func):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        job_func,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id='screenshot_job',
        name='定时截图发送',
        max_instances=1,           # 防止任务堆积
        coalesce=True,             # 错过的合并为一次
        misfire_grace_time=300,    # 允许 5 分钟内的迟触发补跑
    )
    scheduler.start()
    return scheduler
```

### 3.7 息屏阻止方案

软件运行期间阻止系统息屏/睡眠,退出后自动恢复:

```python
import ctypes

# Windows API 常量
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

def keep_awake_on():
    """阻止息屏/睡眠(软件运行时调用)"""
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    )

def keep_awake_off():
    """恢复系统默认电源策略(软件退出时调用)"""
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
```

**设计要点**
- 默认开启,设置里可关
- 首次启动提示用户顺便检查系统电源设置(双重保险)
- 软件退出/崩溃后,Windows 会自动恢复默认策略,不会 "软件关了还不息屏"

### 3.8 推送失败处理(重试 + 告警 + 邮件兜底)

```python
import time, logging

RETRY_DELAYS = [10, 30, 60]  # 秒

def push_with_retry(notify_fn, image_path, fallback_email_fn, email_cfg):
    """带重试 + 兜底的消息推送"""
    for i, delay in enumerate(RETRY_DELAYS, 1):
        try:
            return notify_fn(image_path)  # 主通道(飞书)
        except Exception as e:
            logging.warning(f"第 {i} 次推送失败: {e},{delay}s 后重试")
            time.sleep(delay)

    # 主通道彻底失败 → 邮件兜底
    try:
        fallback_email_fn(image_path, email_cfg)
        tray_alert("飞书推送失败,已改用邮件发送", level='warning')
    except Exception as e:
        logging.error(f"邮件兜底也失败: {e}")
        tray_alert("推送全部失败,请检查网络/绑定", level='error')
```

> 完整的 "本地队列 + 断网恢复后补发" 留作后续版本。因为本地已存所有截图(3.5),未来补发就是 "重发历史文件",成本低。

---

## 四、系统架构

### 4.1 模块划分

```
Screenshot Courier
├── config/
│   └── config_manager.py        # 配置管理 + DPAPI 加密
├── core/
│   ├── screenshot_engine.py     # 截图引擎
│   ├── scheduler.py             # 定时调度
│   ├── storage.py               # 本地存档 + 自动清理
│   └── keep_awake.py            # 息屏阻止
├── binding/
│   └── binding_manager.py       # 多绑定列表管理(增/删/切换/持久化)
├── notification/
│   ├── notification_manager.py  # 推送编排(重试 + 兜底 + 告警)
│   ├── feishu_client.py         # 飞书客户端(registerApp/发图/token 续期)
│   ├── email_client.py          # 邮件客户端
│   └── wecom_client.py          # 企业微信客户端(Plan B,可选)
├── gui/
│   ├── main_window.py
│   ├── settings_dialog.py
│   ├── tray_icon.py             # 状态可见 + 快速操作 + 接收人切换菜单
│   └── binding_dialog.py        # 扫码绑定界面(新增绑定)
└── main.py
```

### 4.2 数据流

```
用户配置(含飞书绑定列表 + 当前激活绑定)
    ↓
ConfigManager 读取配置(凭证解密)
    ↓
BindingManager 提供 "当前激活绑定"
    ↓
Scheduler 初始化定时任务
    ↓
[定时触发]
    ↓
ScreenshotEngine 截图 → Storage 按时间存到本地
    ↓
NotificationManager 推送给 "当前激活绑定"
    ├── 飞书(主): 用该绑定的凭证 → 上传 image_key → 发私聊消息
    │     └─ 失败重试 3 次
    └── 邮件(兜底): 主通道彻底失败时启用
    ↓
TrayIcon 更新状态(成功/重试中/异常告警 + 显示当前接收人)
    ↓
[用户切换接收人] → BindingManager 改 active_binding_id → 下一张图发给新人
    ↓
等待下一个周期
```

### 4.3 配置文件格式

**config.json**(明文项)

```json
{
    "screenshot": {
        "interval_minutes": 15,
        "quality": 80,
        "output_dir": "C:/Users/X/Pictures/ScreenshotCourier"
    },
    "feishu": {
        "enabled": true,
        "active_binding_id": "b_001",
        "bindings": [
            {
                "id": "b_001",
                "label": "张三",
                "app_id": "cli_xxxxxxxxx",
                "receive_id": "ou_xxxxxxxxx",
                "receive_id_type": "open_id",
                "mode": "private",
                "group_chat_id": "",
                "created_at": "2026-06-19T14:15:30"
            },
            {
                "id": "b_002",
                "label": "李四",
                "app_id": "cli_yyyyyyyyy",
                "receive_id": "ou_yyyyyyyyy",
                "receive_id_type": "open_id",
                "mode": "private",
                "group_chat_id": "",
                "created_at": "2026-06-19T15:02:11"
            }
        ]
    },
    "email": {
        "enabled": true,
        "sender": "your_email@example.com",
        "smtp_host": "smtp.example.com",
        "smtp_port": 465,
        "recipient": "recipient@example.com"
    },
    "storage": {
        "retention_days": 30,
        "max_size_gb": 5,
        "auto_clean": true
    },
    "general": {
        "auto_start": false,
        "minimize_to_tray": true,
        "keep_awake": true,
        "log_level": "INFO"
    }
}
```

**说明**
- `feishu.bindings` 是绑定列表,`active_binding_id` 指向当前激活的接收人
- 切换接收人 = 改 `active_binding_id`,不改其他字段
- 单人专用电脑:列表里只有一个绑定,`active_binding_id` 永远指向它

**secrets.dat**(DPAPI 加密,与 config.json 同目录)
- `feishu.bindings[*].app_secret`(按 binding 的 id 索引)
- `email.password`

---

## 五、用户使用流程

### 5.1 首次使用(第一个接收人)

```
1. 双击运行 ScreenshotCourier.exe(或安装后从开始菜单启动)
   ↓
2. 主窗口打开,提示 "尚未绑定任何接收人"
   ↓
3. 点 "新增绑定" → 填姓名备注(如 "张三")→ 弹出二维码
   ↓
4. 用手机飞书扫码确认
   ↓
5. 软件拿到 app_id/secret/open_id,加密保存,设为当前激活
   ↓
6. 引导配置权限(一键复制 JSON + 跳转飞书后台)
   ↓
7. 设置截图间隔(默认 15 分钟)
   ↓
8. (可选)填兜底邮箱
   ↓
9. 点 "开始监控"
   ↓
10. 软件最小化到托盘,自动阻止息屏
```

### 5.2 日常使用(单人)

```
1. 软件开机自启动(可选)
   ↓
2. 自动读取本地绑定列表,无需扫码
   ↓
3. 自动截图 → 存本地 → 飞书私聊推送(发给当前激活接收人)
   ↓
4. 用户在手机飞书查看截图
   ↓
5. 需调整 → 右键托盘 → 打开设置
   ↓
6. 需暂停 → 右键托盘 → 暂停监控
```

### 5.2.1 多人共用(新增绑定 + 切换)

```
新增同门的绑定(每人首次在该电脑各做一次):
1. 右键托盘 → 切换接收人 → ＋ 新增绑定
   ↓
2. 填姓名(如 "李四")→ 扫码 → 存档
   (此后李四在该电脑上永远不用再扫)

日常换人实验:
1. 右键托盘 → 切换接收人 → 选 "李四"
   ↓
2. 下一张截图立即发给李四(无延迟、无扫码)
```

移除已离开的同门:设置页 → 接收人列表 → 删除(不影响其在飞书侧的应用)。

### 5.3 异常处理

| 场景 | 处理 |
|------|------|
| 飞书推送失败 | 自动重试 3 次 → 邮件兜底 + 托盘告警 |
| 网络异常 | 截图照常存本地,恢复后可手动补发(完整自动补发留后续版本) |
| 程序崩溃 | 开机自启动恢复;Windows 自动恢复息屏策略 |
| 飞书凭证失效 | 托盘变红 + 弹窗提示重扫 + 邮件兜底 |

---

## 六、部署方案

### 6.1 打包

```bash
# --onedir:启动快、好升级(替代 v0.1 的 --onefile)
pyinstaller --onedir --windowed --icon=icon.ico main.py
```

再用 **Inno Setup** 封装为 "下一步下一步" 安装包。

### 6.2 用户安装

1. 下载 `ScreenshotCourierSetup.exe`
2. 双击安装(下一步 → 完成)
3. 无需安装 Python 或任何依赖

### 6.3 开机自启动(可选)

通过 Windows 启动文件夹或注册表 Run 项实现,安装时可选勾选。

---

## 七、企业微信 Plan B 备选方案

当飞书方案遇到阻碍(如个别课题组环境限制、用户更熟悉企业微信)时,启用本方案。

### 7.1 方案要点

- **企业微信群机器人 Webhook**:群内添加机器人,拿到一个 webhook URL
- 发图片为**一步 POST**(base64),实现比飞书更简单
- 零审核、零应用、永久免费稳定

### 7.2 与飞书方案的差异

| | 飞书(registerApp) | 企业微信群机器人 |
|---|---|---|
| 首次配置 | 扫码建应用 + 配权限 | 群里加机器人,复制 URL |
| 配置耗时 | ~5 分钟(有教程) | ~2 分钟 |
| 发图片 | 两步(上传 + 发) | 一步 POST |
| 体验上限 | 高(扫码仪式感、卡片) | 中(往群里甩图) |
| 代码量 | 多(token 续期等) | 少 |

### 7.3 切换策略

- `wecom_client.py` 实现 `WeComClient` 类,接口与 `FeishuClient` 一致
- `NotificationManager` 按配置 `notify_channel: 'feishu' | 'wecom'` 选择
- 后续可考虑做成 "飞书失败自动降级到企业微信"

---

## 八、待验证事项(开发前需实测)

1. **飞书 `registerApp` 在 Python SDK 中的可用性** — 官方文档以 Node SDK 为例,需确认 `lark-oapi`(Python)是否提供等价方法;若无,需自行实现 RFC 8628 Device Flow
2. **飞书应用权限配置是否真的免审** — Device Flow 创建的应用开权限是否仍需企业管理员确认
3. **飞书图片大小/频率限制** — 高频推送是否触发限流
4. **锁屏/会话切换时的截图表现** — 虽然开启了 keep_awake,仍需验证 RDP/锁屏场景 MSS 是否黑屏
5. **`tenant_access_token` 续期边界** — 并发推送时的 token 竞争

---

## 九、项目结构

```
Screenshot Courier/
├── src/
│   ├── config/
│   │   └── config_manager.py
│   ├── core/
│   │   ├── screenshot_engine.py
│   │   ├── scheduler.py
│   │   ├── storage.py
│   │   └── keep_awake.py
│   ├── notification/
│   │   ├── notification_manager.py
│   │   ├── feishu_client.py
│   │   ├── email_client.py
│   │   └── wecom_client.py
│   ├── gui/
│   │   ├── main_window.py
│   │   ├── settings_dialog.py
│   │   ├── binding_dialog.py
│   │   └── tray_icon.py
│   └── main.py
├── resources/
│   └── icon.ico
├── requirements.txt
├── build.spec
├── installer.iss          # Inno Setup 脚本
└── README.md
```

---

## 十、技术参考

### 10.1 关键库文档

- MSS:https://python-mss.readthedocs.io/
- APScheduler:https://apscheduler.readthedocs.io/
- yagmail:https://github.com/kootenpv/yagmail
- PySide6:https://www.qt.io/python
- PyInstaller:https://pyinstaller.org/
- Lark Python SDK (`lark-oapi`):https://open.feishu.cn/document/server-side-sdk/python--sdk

### 10.2 飞书官方文档

- 扫码一键创建应用(NodeJS 版原理,Python 需对照实现):
  https://open.feishu.cn/document/mcp_open_tools/integrating-agents-with-feishu/scan-to-create-an-app-in-one-click-nodejs
- Lark SDK registerApp 说明:https://github.com/larksuite/node-sdk/blob/main/README.zh.md
- 图片上传接口:`POST /open-apis/im/v1/images`
- 发消息接口:`POST /open-apis/im/v1/messages`

### 10.3 参考实现

- Proma 项目的 `feishu-bridge.ts` / `feishu-config.ts` / `ipc.ts`(扫码绑定与凭证加密持久化的工程实践)

---

## 十一、总结

Screenshot Courier v0.2 是面向生化环材专业研究人员的实验监控工具,通过定时截图和自动推送,让用户远程查看实验电脑屏幕状态。

**核心优势**
- 安装即用,无需技术背景
- 飞书扫码一键绑定,长期免扫码
- **多绑定快速切换**,适配多人共用仪器场景
- 主(飞书)+ 兜(邮件)双通道,稳定可靠
- 截图本地存档,可回溯不丢数据
- 托盘运行 + 运行时阻止息屏,不干扰实验

**技术方案**
- 截图:MSS(高性能、低占用)
- 定时:APScheduler(灵活调度)
- 主推送:飞书 Lark SDK `registerApp` 扫码绑定
- 兜底推送:邮件 SMTP
- Plan B:企业微信群机器人
- 界面:PySide6 系统托盘
- 打包:PyInstaller(`--onedir`) + Inno Setup
