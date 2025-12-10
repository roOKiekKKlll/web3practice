# 快速开始

## 3 分钟上手

```bash
# 1. 安装
pip install -r requirements.txt

# 2. 配置账号
python manage_cookies.py  # 添加 2-3 个小号

# 3. 编辑 config.py
#    - MONITORED_USERS = ["用户名"]
#    - WECHAT_SENDKEY = "你的SendKey"  # 从 sct.ftqq.com 获取

# 4. 运行
python run_monitor_final.py
```

## 常用命令

```bash
# 账号管理
python manage_cookies.py

# 导出单个账号（旧方式）
python export_cookies.py

# 运行监控
python run_monitor_final.py

# 后台运行
nohup python3 run_monitor_final.py > monitor.log 2>&1 &

# 停止
pkill -f run_monitor_final.py
```

## 配置示例

### config.py
```python
MONITORED_USERS = ["elonmusk", "VitalikButerin"]
CHECK_INTERVAL = 30
WECHAT_SENDKEY = "SCT123456..."
ENABLE_WECHAT_PUSH = True
```

### twitter_cookies.json
```json
{
  "accounts": [
    {
      "name": "小号1",
      "auth_token": "cdac2eff...",
      "ct0": "40be02af...",
      "enabled": true
    },
    {
      "name": "小号2",
      "auth_token": "e7f92ba3...",
      "ct0": "89ac5de2...",
      "enabled": true
    }
  ]
}
```

## 获取 Cookies

1. 登录 https://x.com
2. F12 → Application → Cookies
3. 复制 `auth_token` 和 `ct0`
4. 运行 `python manage_cookies.py` 添加

## 获取 Server酱 SendKey

1. 访问 https://sct.ftqq.com/
2. 微信扫码登录
3. 复制 SendKey

---

详细文档见 [README.md](README.md)

