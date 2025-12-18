# Fight.ID Scripts Configuration Example
# 复制此文件为 config.py 并填写你的配置

# ==================== IMAP 邮箱配置 ====================
IMAP_CONFIG = {
    "PASSWORD": "YOUR_IMAP_PASSWORD",  # IMAP 邮箱密码
    "SERVER": "imap.example.com",       # IMAP 服务器地址
    "PORT": 993,                        # IMAP 端口 (SSL)
    "USE_SSL": True                     # 是否使用 SSL
}

# ==================== BSC RPC 节点 ====================
RPC_URLS = [
    'https://bsc-dataseed.binance.org/',
    'https://bsc-dataseed1.defibit.io/',
    'https://bsc-dataseed1.ninicoin.io/',
]

# ==================== Gas 分发配置 ====================
GAS_CONFIG = {
    "MIN_AMOUNT_BNB": 0.00007,  # 最小分发金额
    "MAX_AMOUNT_BNB": 0.00011,  # 最大分发金额
    "DELAY_BETWEEN_TX": 0.5    # 交易间隔 (秒)
}

# ==================== 推荐码配置 ====================
REFERRAL_CONFIG = {
    "MIN_USES": 8,   # 每个推荐码最小使用次数
    "MAX_USES": 15   # 每个推荐码最大使用次数
}

# ==================== 并发配置 ====================
CONCURRENT_CONFIG = {
    "MAX_WORKERS": 5,         # 最大并发数
    "DELAY_BETWEEN_TASKS": 0.5  # 任务间隔 (秒)
}

