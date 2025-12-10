"""
最终版监控脚本 - 使用 requests + GraphQL API
"""

from twitter_monitor_requests import TwitterMonitorRequests
from wechat_push import WechatPusher
import config
from pathlib import Path

def main():
    cookies_file = config.COOKIES_FILE
    
    if not Path(cookies_file).exists():
        print("=" * 60)
        print("❌ 错误: 找不到 cookies 文件")
        print("=" * 60)
        print("请先运行: python export_cookies.py")
        print("从 x.com 导出你的 cookies")
        print("=" * 60)
        return
    
    if not config.MONITORED_USERS:
        print("❌ 错误: 请在 config.py 中配置要监控的用户")
        return
    
    # 创建监控器
    try:
        monitor = TwitterMonitorRequests(cookies_file, output_dir=config.OUTPUT_DIR)
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return
    
    # 初始化微信推送（个人通知）
    wechat_pusher = None
    if config.ENABLE_WECHAT_PUSH and config.WECHAT_SENDKEY:
        wechat_pusher = WechatPusher(config.WECHAT_SENDKEY)
        print("✓ 微信个人推送已启用（Server酱）")
    
    print()
    print("=" * 60)
    print(f"开始监控 {len(config.MONITORED_USERS)} 个用户")
    print(f"用户: {', '.join(['@' + u for u in config.MONITORED_USERS])}")
    print(f"检查间隔: {config.CHECK_INTERVAL} 秒")
    print("=" * 60)
    print()
    
    # 如果只监控一个用户
    if len(config.MONITORED_USERS) == 1:
        monitor.monitor_user(
            username=config.MONITORED_USERS[0],
            interval=config.CHECK_INTERVAL,
            max_tweets=config.MAX_TWEETS_PER_CHECK,
            wechat_pusher=wechat_pusher
        )
    else:
        # 多个用户 - 依次检查
        monitor.monitor_multiple_users(
            usernames=config.MONITORED_USERS,
            interval=config.CHECK_INTERVAL,
            max_tweets=config.MAX_TWEETS_PER_CHECK,
            wechat_pusher=wechat_pusher
        )

if __name__ == "__main__":
    main()
