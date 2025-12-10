"""
Twitter 监控工具 - 直接使用 requests + cookies
支持多账号轮询，避免单账号风控
"""

import json
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import random

class TwitterMonitorRequests:
    def __init__(self, cookies_file: str, output_dir: str = "monitor_data"):
        """
        初始化 Twitter 监控器（支持多账号轮询）
        
        Args:
            cookies_file: Cookies 文件路径
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.monitored_tweets = {}
        self.cookies_file = cookies_file
        
        # 账号池管理
        self.accounts = []  # 所有可用账号
        self.current_account_index = 0  # 当前使用的账号索引
        self.account_requests = {}  # 每个账号的请求计数
        self.account_last_used = {}  # 每个账号的最后使用时间
        self.max_requests_per_account = 50  # 单账号最大连续请求数
        
        # 基础请求头模板
        self.base_headers = {
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://x.com/home',
            'Origin': 'https://x.com',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'x-twitter-active-user': 'yes',
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-client-language': 'zh-cn',
        }
        
        # 加载多账号配置
        self._load_accounts()
        
        if not self.accounts:
            raise ValueError("没有可用的账号！请检查 cookies 文件")
        
        # 初始化当前账号
        self._switch_to_next_account()
        
        print(f"✓ 多账号轮询已启用，共 {len(self.accounts)} 个账号")
    
    def _load_accounts(self):
        """加载账号配置（支持单账号和多账号格式）"""
        if not Path(self.cookies_file).exists():
            raise FileNotFoundError(f"找不到 cookies 文件: {self.cookies_file}")
        
        with open(self.cookies_file, 'r', encoding='utf-8') as f:
            cookies_data = json.load(f)
        
        # 判断是新格式（多账号）还是旧格式（单账号）
        if 'accounts' in cookies_data:
            # 新格式：多账号
            for idx, account in enumerate(cookies_data['accounts']):
                if account.get('enabled', True):  # 只加载启用的账号
                    self.accounts.append({
                        'name': account.get('name', f'账号{idx+1}'),
                        'auth_token': account['auth_token'],
                        'ct0': account['ct0'],
                        'index': idx
                    })
                    self.account_requests[idx] = 0
                    self.account_last_used[idx] = 0
            print(f"✓ 加载了 {len(self.accounts)} 个账号（多账号模式）")
        else:
            # 旧格式：单账号（兼容）
            self.accounts.append({
                'name': '默认账号',
                'auth_token': cookies_data['auth_token'],
                'ct0': cookies_data['ct0'],
                'index': 0
            })
            self.account_requests[0] = 0
            self.account_last_used[0] = 0
            print(f"✓ 加载了 1 个账号（单账号模式）")
    
    def _switch_to_next_account(self):
        """切换到下一个可用账号"""
        if not self.accounts:
            raise ValueError("没有可用的账号")
        
        # 选择请求数最少的账号
        min_requests = min(self.account_requests.values())
        available_accounts = [
            idx for idx, count in self.account_requests.items()
            if count == min_requests
        ]
        
        # 从请求数最少的账号中随机选一个
        self.current_account_index = random.choice(available_accounts)
        account = self.accounts[self.current_account_index]
        
        # 更新 cookies 和 headers
        self.cookies = {
            'auth_token': account['auth_token'],
            'ct0': account['ct0']
        }
        
        self.headers = self.base_headers.copy()
        self.headers['x-csrf-token'] = account['ct0']
        
        # 更新最后使用时间
        self.account_last_used[self.current_account_index] = time.time()
        
        print(f"✓ 切换到账号: {account['name']} (请求数: {self.account_requests[self.current_account_index]})")
    
    def _get_current_account(self) -> Dict:
        """获取当前使用的账号信息"""
        return self.accounts[self.current_account_index]
    
    def _record_request(self):
        """记录一次请求，并检查是否需要切换账号"""
        self.account_requests[self.current_account_index] += 1
        
        # 如果当前账号请求数过多，切换到下一个
        if self.account_requests[self.current_account_index] >= self.max_requests_per_account:
            current = self._get_current_account()
            print(f"⚠ 账号 {current['name']} 已达到请求上限，切换账号...")
            
            # 重置当前账号的计数
            self.account_requests[self.current_account_index] = 0
            
            # 切换到下一个账号
            if len(self.accounts) > 1:
                self._switch_to_next_account()
    
    def _handle_request_error(self, status_code: int):
        """处理请求错误，可能需要切换账号"""
        if status_code in [429, 403]:  # 速率限制或禁止访问
            current = self._get_current_account()
            print(f"⚠ 账号 {current['name']} 遇到限制 ({status_code})，切换账号...")
            
            # 标记当前账号暂时不可用（大幅增加计数）
            self.account_requests[self.current_account_index] += 100
            
            # 切换账号
            if len(self.accounts) > 1:
                self._switch_to_next_account()
                time.sleep(2)  # 短暂等待
    
    def get_user_tweets(self, username: str, max_tweets: int = 20) -> List[Dict]:
        """
        获取指定用户的最新推特
        使用 GraphQL API (X.com 网页版使用的 API)
        """
        try:
            print(f"正在获取 @{username} 的推特...")
            
            # 使用 GraphQL API - UserTweets
            # 这个 query_id 是从 X.com 网页版抓包得到的
            url = "https://x.com/i/api/graphql/E3opETHurmVJflFsUBVuUQ/UserTweets"
            
            # 构建变量
            variables = {
                "userId": "",  # 需要先获取 user_id
                "count": max_tweets,
                "includePromotedContent": True,
                "withQuickPromoteEligibilityTweetFields": True,
                "withVoice": True,
                "withV2Timeline": True
            }
            
            # 首先需要获取用户的 user_id
            # 使用 UserByScreenName API
            user_url = "https://x.com/i/api/graphql/G3KGOASz96M-Qu0nwmGXNg/UserByScreenName"
            user_variables = {
                "screen_name": username,
                "withSafetyModeUserFields": True
            }
            user_features = {
                "hidden_profile_likes_enabled": False,
                "hidden_profile_subscriptions_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "subscriptions_verification_info_is_identity_verified_enabled": True,
                "subscriptions_verification_info_verified_since_enabled": True,
                "highlights_tweets_tab_ui_enabled": True,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True
            }
            
            user_params = {
                'variables': json.dumps(user_variables),
                'features': json.dumps(user_features)
            }
            
            # 获取用户信息
            self._record_request()  # 记录请求
            
            user_response = requests.get(
                user_url,
                headers=self.headers,
                cookies=self.cookies,
                params=user_params,
                timeout=15
            )
            
            if user_response.status_code != 200:
                print(f"✗ 获取用户信息失败: {user_response.status_code}")
                self._handle_request_error(user_response.status_code)  # 处理错误
                print(f"响应: {user_response.text[:300]}")
                return []
            
            # requests 会自动处理解压
            try:
                user_data = user_response.json()
            except Exception as e:
                print(f"✗ 解析用户数据失败: {e}")
                return []
            
            # 提取 user_id
            try:
                user_id = user_data['data']['user']['result']['rest_id']
                print(f"✓ 获取到用户ID: {user_id}")
            except KeyError:
                print(f"✗ 无法提取用户ID，响应结构: {list(user_data.keys())}")
                return []
            
            # 现在获取推特
            variables['userId'] = user_id
            
            features = {
                "rweb_lists_timeline_redesign_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": False,
                "tweet_awards_web_tipping_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_media_download_video_enabled": False,
                "responsive_web_enhance_cards_enabled": False,
                "rweb_tipjar_consumption_enabled": True,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "articles_preview_enabled": True,
                "rweb_video_timestamps_enabled": True,
                "communities_web_enable_tweet_community_results_fetch": True,
                "responsive_web_text_conversations_enabled": False,
                "longform_notetweets_consumption_enabled": True
            }
            
            params = {
                'variables': json.dumps(variables),
                'features': json.dumps(features)
            }
            
            self._record_request()  # 记录请求
            
            response = requests.get(
                url,
                headers=self.headers,
                cookies=self.cookies,
                params=params,
                timeout=15
            )
            
            print(f"推特 API 响应状态: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    # requests 会自动处理 gzip/brotli 解压，直接解析 JSON
                    data = response.json()
                except Exception as e:
                    print(f"✗ JSON 解析失败: {e}")
                    print(f"Content-Encoding: {response.headers.get('Content-Encoding')}")
                    print(f"响应内容前100字符: {response.content[:100]}")
                    return []
                
                tweet_list = []
                
                # 解析 GraphQL 响应
                try:
                    instructions = data['data']['user']['result']['timeline_v2']['timeline']['instructions']
                    
                    for instruction in instructions:
                        if instruction.get('type') == 'TimelineAddEntries':
                            entries = instruction.get('entries', [])
                            
                            for entry in entries:
                                if 'content' not in entry:
                                    continue
                                
                                content = entry['content']
                                if content.get('entryType') != 'TimelineTimelineItem':
                                    continue
                                
                                if 'itemContent' not in content:
                                    continue
                                
                                item = content['itemContent']
                                if item.get('itemType') != 'TimelineTweet':
                                    continue
                                
                                if 'tweet_results' not in item:
                                    continue
                                
                                tweet_result = item['tweet_results'].get('result', {})
                                if 'legacy' not in tweet_result:
                                    continue
                                
                                legacy = tweet_result['legacy']
                                
                                # 提取推特信息
                                text = legacy.get('full_text', '')
                                tweet_id = legacy.get('id_str', '')
                                
                                # 检查是否是转推
                                is_retweet = 'retweeted_status_result' in legacy
                                if is_retweet:
                                    # 如果是转推，提取原始推特的信息
                                    retweeted = legacy.get('retweeted_status_result', {}).get('result', {})
                                    if 'legacy' in retweeted:
                                        original_text = retweeted['legacy'].get('full_text', '')
                                        original_user = retweeted.get('core', {}).get('user_results', {}).get('result', {}).get('legacy', {}).get('screen_name', '')
                                        # 组合转推格式
                                        text = f"RT @{original_user}: {original_text}"
                                
                                # 获取用户的真实 screen_name（用于确认是本人）
                                user_info = tweet_result.get('core', {}).get('user_results', {}).get('result', {}).get('legacy', {})
                                actual_username = user_info.get('screen_name', username)
                                
                                # 只保留本人的推特（不是其他人的）
                                if actual_username.lower() != username.lower():
                                    continue
                                
                                # 转换时间为北京时间
                                utc_time_str = legacy.get('created_at', '')
                                beijing_time_str = utc_time_str
                                try:
                                    # 解析 Twitter 时间格式: "Mon Dec 08 07:45:50 +0000 2025"
                                    utc_time = datetime.strptime(utc_time_str, '%a %b %d %H:%M:%S %z %Y')
                                    # 转换为北京时间 (UTC+8)
                                    beijing_time = utc_time.astimezone(timezone(timedelta(hours=8)))
                                    beijing_time_str = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
                                except:
                                    pass
                                
                                tweet_data = {
                                    'tweet_id': tweet_id,
                                    'username': username,
                                    'text': text,
                                    'date': beijing_time_str,
                                    'date_utc': utc_time_str,  # 保留原始 UTC 时间
                                    'stats': {
                                        'likes': legacy.get('favorite_count', 0),
                                        'retweets': legacy.get('retweet_count', 0),
                                        'replies': legacy.get('reply_count', 0),
                                    },
                                    'link': f"https://x.com/{username}/status/{tweet_id}",
                                    'is_reply': legacy.get('in_reply_to_status_id_str') is not None,
                                    'is_retweet': is_retweet,
                                    'timestamp': datetime.now().isoformat()
                                }
                                tweet_list.append(tweet_data)
                    
                    print(f"✓ 成功获取 {len(tweet_list)} 条推特")
                    return tweet_list
                    
                except Exception as e:
                    print(f"✗ 解析响应失败: {e}")
                    print(f"响应结构: {list(data.keys())}")
                    return []
            else:
                print(f"✗ 获取失败: {response.status_code}")
                self._handle_request_error(response.status_code)  # 处理错误
                print(f"响应: {response.text[:300]}")
                return []
                
        except Exception as e:
            print(f"✗ 获取推特时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def save_data(self, username: str, tweets: List[Dict], data_type: str = "tweets"):
        """保存数据到文件"""
        if not tweets:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{username}_{data_type}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(tweets, f, ensure_ascii=False, indent=2)
            print(f"✓ 数据已保存到: {filepath}")
        except Exception as e:
            print(f"✗ 保存数据时出错: {str(e)}")
    
    def get_new_tweets(self, username: str, max_tweets: int = 20) -> List[Dict]:
        """获取新的推特（过滤掉已经监控过的）"""
        all_tweets = self.get_user_tweets(username, max_tweets)
        
        if username not in self.monitored_tweets:
            self.monitored_tweets[username] = set()
        
        new_tweets = []
        for tweet in all_tweets:
            tweet_id = tweet.get('tweet_id')
            if tweet_id and tweet_id not in self.monitored_tweets[username]:
                new_tweets.append(tweet)
                self.monitored_tweets[username].add(tweet_id)
        
        return new_tweets
    
    def monitor_user(self, username: str, interval: int = 30, max_tweets: int = 20, wechat_pusher=None):
        """持续监控指定用户"""
        print(f"开始监控 @{username}")
        print(f"检查间隔: {interval} 秒")
        print("=" * 50)
        
        # 首次运行
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 首次获取数据...")
        initial_tweets = self.get_user_tweets(username, max_tweets)
        
        if username not in self.monitored_tweets:
            self.monitored_tweets[username] = set()
        for tweet in initial_tweets:
            tweet_id = tweet.get('tweet_id')
            if tweet_id:
                self.monitored_tweets[username].add(tweet_id)
        
        print(f"初始化完成，已记录 {len(initial_tweets)} 条推特")
        
        # 持续监控
        try:
            while True:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查新推特...")
                
                new_tweets = self.get_new_tweets(username, max_tweets)
                
                if new_tweets:
                    print(f"🆕 发现 {len(new_tweets)} 条新内容!")
                    
                    # 分类
                    pure_tweets = [t for t in new_tweets if not t.get('is_reply') and not t.get('is_retweet')]
                    replies = [t for t in new_tweets if t.get('is_reply')]
                    retweets = [t for t in new_tweets if t.get('is_retweet')]
                    
                    # 输出最新内容并推送到微信
                    if pure_tweets:
                        self.save_data(username, pure_tweets, "tweets")
                        latest = pure_tweets[0]
                        print(f"\n📝 最新推特:")
                        print(f"时间: {latest['date']}")
                        print(f"内容: {latest['text']}")
                        print(f"链接: {latest['link']}")
                        print(f"点赞: {latest['stats']['likes']} | 转发: {latest['stats']['retweets']}")
                        
                        # 推送到微信
                        if wechat_pusher:
                            wechat_pusher.send_tweet_update(username, latest)
                    
                    if replies:
                        self.save_data(username, replies, "replies")
                        latest = replies[0]
                        print(f"\n💬 最新回复:")
                        print(f"时间: {latest['date']}")
                        print(f"内容: {latest['text']}")
                        print(f"链接: {latest['link']}")
                        
                        # 推送到微信
                        if wechat_pusher:
                            wechat_pusher.send_tweet_update(username, latest)
                    
                    if retweets:
                        self.save_data(username, retweets, "retweets")
                        latest = retweets[0]
                        print(f"\n🔄 最新转推:")
                        print(f"时间: {latest['date']}")
                        print(f"内容: {latest['text'][:200]}...")
                        
                        # 推送到微信
                        if wechat_pusher:
                            wechat_pusher.send_tweet_update(username, latest)
                else:
                    print("未发现新内容")
                
                print(f"\n等待 {interval} 秒后继续...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n监控已停止")
        except Exception as e:
            print(f"\n✗ 监控出错: {str(e)}")


    def monitor_multiple_users(self, usernames: List[str], interval: int = 30, max_tweets: int = 20, wechat_pusher=None):
        """监控多个用户"""
        print(f"开始监控 {len(usernames)} 个用户")
        print(f"检查间隔: {interval} 秒")
        print(f"=" * 50)
        
        # 首次运行
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 首次获取数据...")
        for username in usernames:
            initial_tweets = self.get_user_tweets(username, max_tweets)
            if username not in self.monitored_tweets:
                self.monitored_tweets[username] = set()
            for tweet in initial_tweets:
                tweet_id = tweet.get('tweet_id')
                if tweet_id:
                    self.monitored_tweets[username].add(tweet_id)
            time.sleep(2)
        
        print(f"初始化完成")
        
        # 持续监控
        try:
            while True:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查新推特...")
                
                for username in usernames:
                    print(f"\n检查 @{username}...")
                    new_tweets = self.get_new_tweets(username, max_tweets)
                    
                    if new_tweets:
                        print(f"🆕 发现 {len(new_tweets)} 条新内容!")
                        
                        # 分类
                        pure_tweets = [t for t in new_tweets if not t.get('is_reply') and not t.get('is_retweet')]
                        replies = [t for t in new_tweets if t.get('is_reply')]
                        retweets = [t for t in new_tweets if t.get('is_retweet')]
                        
                        # 输出并推送
                        if pure_tweets:
                            self.save_data(username, pure_tweets, "tweets")
                            latest = pure_tweets[0]
                            print(f"\n📝 最新推特:")
                            print(f"时间: {latest['date']}")
                            print(f"内容: {latest['text']}")
                            print(f"链接: {latest['link']}")
                            if wechat_pusher:
                                wechat_pusher.send_tweet_update(username, latest)
                        
                        if replies:
                            self.save_data(username, replies, "replies")
                            latest = replies[0]
                            print(f"\n💬 最新回复:")
                            print(f"时间: {latest['date']}")
                            print(f"内容: {latest['text']}")
                            print(f"链接: {latest['link']}")
                            if wechat_pusher:
                                wechat_pusher.send_tweet_update(username, latest)
                        
                        if retweets:
                            self.save_data(username, retweets, "retweets")
                            latest = retweets[0]
                            print(f"\n🔄 最新转推:")
                            print(f"时间: {latest['date']}")
                            print(f"内容: {latest['text'][:150]}...")
                            if wechat_pusher:
                                wechat_pusher.send_tweet_update(username, latest)
                    else:
                        print("未发现新内容")
                    
                    time.sleep(2)
                
                print(f"\n等待 {interval} 秒后继续...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n监控已停止")
        except Exception as e:
            print(f"\n✗ 监控出错: {str(e)}")


def main():
    """测试"""
    import sys
    
    cookies_file = "twitter_cookies.json"
    if not Path(cookies_file).exists():
        print("❌ 找不到 cookies 文件")
        print("请先运行: python export_cookies.py")
        sys.exit(1)
    
    monitor = TwitterMonitorRequests(cookies_file)
    
    # 测试获取推特
    tweets = monitor.get_user_tweets("elonmusk", max_tweets=10)
    if tweets:
        print(f"\n✅ 成功获取 {len(tweets)} 条推特!")
        for i, t in enumerate(tweets[:3], 1):
            print(f"\n{i}. {t['text'][:100]}...")
            print(f"   链接: {t['link']}")
    else:
        print("\n⚠️ 未获取到推特，请检查:")
        print("1. cookies 是否从 x.com 导出")
        print("2. cookies 是否包含 auth_token 和 ct0")
        print("3. 账号是否正常登录")


if __name__ == "__main__":
    main()

