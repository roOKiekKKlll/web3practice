# Twitter 监控 + 微信推送

监控指定 Twitter 用户的推特和回复，自动推送到微信。支持多账号轮询避免风控。

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置账号

**单账号模式：**
```bash
python export_cookies.py
```
按提示从 x.com 导出 cookies。

**多账号模式（推荐）：**
```bash
python manage_cookies.py
```
添加 2-5 个小号，系统会自动轮询避免风控。

### 3. 配置监控

编辑 `config.py`：
```python
MONITORED_USERS = ["elonmusk", "VitalikButerin"]  # 监控的用户
CHECK_INTERVAL = 30  # 检查间隔（秒）

# Server酱推送（个人微信）
WECHAT_SENDKEY = "你的SendKey"  # 从 https://sct.ftqq.com/ 获取
ENABLE_WECHAT_PUSH = True

# 微信群推送（仅 Windows）
ENABLE_GROUP_BOT = False
WECHAT_GROUP_NAME = "你的群名"
```

### 4. 运行
```bash
python run_monitor_final.py
```

## 多账号轮询

为避免单账号被风控，建议配置多个小号：

```bash
python manage_cookies.py
# 选择"添加新账号"，输入 auth_token 和 ct0
```

系统会：
- 自动轮换账号
- 单账号达到限制自动切换
- 遇到 429/403 错误立即切换

**配置建议：**
- 监控 1-2 用户 → 2 个账号
- 监控 3-5 用户 → 3-4 个账号
- 监控 5+ 用户 → 5 个账号

## 微信群功能（Windows）

1. 安装 wcferry: `pip install wcferry`
2. 登录微信 PC 客户端
3. 配置 `config.py` 中的 `ENABLE_GROUP_BOT` 和 `WECHAT_GROUP_NAME`
4. 运行监控

## 核心文件

```
twitter_moniter/
├── run_monitor_final.py      # 主程序
├── twitter_monitor_requests.py  # 监控核心
├── config.py                  # 配置文件
├── manage_cookies.py          # 多账号管理
├── export_cookies.py          # 导出 cookies
├── wechat_push.py            # Server酱推送
├── wechat_group_bot.py       # 微信群机器人（Windows）
├── requirements.txt          # 依赖
└── twitter_cookies.json      # Cookies 配置
```

## 注意事项

- ⚠️ Cookies 会过期，定期更新
- ⚠️ 不要分享 `twitter_cookies.json`
- ⚠️ 检查间隔不要太短（建议 ≥ 30 秒）
- ⚠️ Server酱免费版每天 5 条推送

---

祝使用愉快！🎉
