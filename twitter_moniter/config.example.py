"""
配置文件示例
复制此文件为 config.py 并填写你的配置
"""

# 需要监控的 Twitter 用户名列表（不含 @ 符号）
MONITORED_USERS = [
    "elonmusk",
    # "BillGates",
    # "naval",
    # 在这里添加更多用户...
]

# 检查间隔时间（秒）
# 建议设置为 300 秒（5分钟）或更长，避免被封禁
CHECK_INTERVAL = 300

# 每次获取的最大推特数量
MAX_TWEETS_PER_CHECK = 20

# 是否包含转推（True=包含，False=只看原创内容和回复）
INCLUDE_RETWEETS = True

# 方式 1：使用 Cookies（推荐，更安全）
# 将浏览器的 Twitter cookies 导出到文件
COOKIES_FILE = "twitter_cookies.json"  # Cookies 文件路径

# 方式 2：使用用户名密码（备用）
TWITTER_USERNAME = ""  # 你的 Twitter 用户名或邮箱
TWITTER_PASSWORD = ""  # 你的 Twitter 密码

# 输出目录
OUTPUT_DIR = "monitor_data"

# 微信推送配置（使用 Server酱 - 个人通知）
# 获取 SendKey: https://sct.ftqq.com/
WECHAT_SENDKEY = ""  # 填写你的 Server酱 SendKey
ENABLE_WECHAT_PUSH = False  # 是否启用微信推送

