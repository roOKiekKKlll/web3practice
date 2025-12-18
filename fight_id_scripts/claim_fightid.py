# Fight.ID Claim FightID Script
# 批量 Claim FightID

import requests
import time
import random
import uuid
import csv
import os
from datetime import datetime
import string

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/115.0.1900.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
]


class FightIDClaimer:
    def __init__(self):
        self.session = requests.Session()

        self.base_headers = {
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'User-Agent': random.choice(user_agents),
            'Referer': 'https://app.fight.id',
            'Origin': 'https://app.fight.id',
            'accept': '*/*',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'content-type': 'application/json'
        }

        self.session.headers.update(self.base_headers)

    def _generate_dynamic_headers(self):
        """生成动态的sentry头部"""
        trace_id = str(uuid.uuid4()).replace('-', '')[:32]
        span_id = str(uuid.uuid4())[:16]

        return {
            'baggage': f'sentry-environment=prod,sentry-release=322e03722b5b3b9cb6009bd85565a5034efe634b,sentry-public_key=90dba384c939a12a890c037474951990,sentry-trace_id={trace_id},sentry-sample_rate=0.1,sentry-sampled=false',
            'sentry-trace': f'{trace_id}-{span_id}-0'
        }

    def _generate_random_username(self, length_range=(15, 25)):
        """生成随机用户名"""
        min_len, max_len = length_range
        length = random.randint(min_len, max_len)
        characters = string.ascii_letters + string.digits
        username = ''.join(random.choice(characters) for _ in range(length))
        return username

    def read_token_csv(self, file_path="tokens.csv"):
        """读取tokens.csv文件，过滤掉token为空的行"""
        tokens_data = []
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    wallet = row.get('wallet', '').strip()
                    token = row.get('token', '').strip()
                    updated_time = row.get('更新时间', '').strip()

                    if wallet and token:
                        tokens_data.append({
                            'wallet': wallet,
                            'token': token,
                            '更新时间': updated_time
                        })

            valid_count = len(tokens_data)
            total_count = sum(1 for _ in open(file_path, 'r', encoding='utf-8')) - 1
            print(
                f"✅ 从 {file_path} 读取到 {valid_count} 个有效钱包（共 {total_count} 行，跳过 {total_count - valid_count} 个空token行）")
            return tokens_data

        except FileNotFoundError:
            print(f"❌ 文件 {file_path} 未找到")
            return []
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return []

    def claim_fightid_for_wallet(self, wallet_address, access_token, max_retries=3):
        """为单个钱包调用claim-fightid接口"""
        url = "https://api.fight.id/user/claim-fightid"

        email = f"{wallet_address.lower()}@temp.wallet"
        username = self._generate_random_username()
        referral_code = ""
        referral_source = ""

        request_data = {
            "email": email,
            "username": username,
            "referralCode": referral_code,
            "referralSource": referral_source
        }

        dynamic_headers = self._generate_dynamic_headers()
        claim_headers = {
            **self.base_headers,
            **dynamic_headers,
            'accept-language': 'ja',
            'authorization': f'Bearer {access_token}',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=1, i'
        }

        for attempt in range(max_retries):
            try:
                print(f"🔄 钱包 {wallet_address[:12]}... (尝试 {attempt + 1}/{max_retries})")
                print(f"   📧 邮箱: {email}")
                print(f"   👤 用户名: {username}")

                response = self.session.post(url, headers=claim_headers, json=request_data, timeout=15)
                print(f"   📥 状态码: {response.status_code}")

                if response.status_code == 201:
                    result = response.json()

                    data = result.get('data', {})
                    fightid_token = data.get('accessToken', '')
                    returned_username = data.get('username', username)
                    returned_email = data.get('email', email)
                    user_id = data.get('userId', '')
                    verified = data.get('verified', False)

                    print(f"   ✅ 成功！Username: {returned_username}")

                    return {
                        'success': True,
                        'status_code': 201,
                        'wallet': wallet_address,
                        'email': returned_email,
                        'username': returned_username,
                        'fightid_token': fightid_token,
                        'user_id': user_id,
                        'verified': verified,
                        'request_data': request_data,
                        'response': result,
                        'attempts': attempt + 1
                    }

                elif response.status_code == 400:
                    error_msg = f"请求参数错误或用户已存在"
                    print(f"   ❌ {error_msg}")
                    return {
                        'success': False,
                        'status_code': 400,
                        'wallet': wallet_address,
                        'email': email,
                        'username': username,
                        'error': error_msg,
                        'response_text': response.text,
                        'attempts': attempt + 1
                    }

                elif response.status_code == 401:
                    error_msg = f"Authorization失败，access_token无效"
                    print(f"   ❌ {error_msg}")
                    return {
                        'success': False,
                        'status_code': 401,
                        'wallet': wallet_address,
                        'email': email,
                        'username': username,
                        'error': error_msg,
                        'response_text': response.text,
                        'attempts': attempt + 1
                    }

                elif response.status_code == 429:
                    wait_time = (2 ** attempt) + random.uniform(0.1, 0.5)
                    print(f"   ⏳ 频率限制，等待 {wait_time:.2f}秒")
                    time.sleep(wait_time)
                    continue

                else:
                    print(f"   ❌ HTTP错误: {response.status_code}")
                    print(f"   🔍 响应内容: {response.text}")

                    if attempt < max_retries - 1:
                        wait_time = 1 + attempt
                        print(f"   ⏳ 等待 {wait_time}秒后重试...")
                        time.sleep(wait_time)
                        continue

            except requests.exceptions.RequestException as e:
                print(f"   ❌ 网络请求异常: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue

            except Exception as e:
                print(f"   ❌ 未知异常: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue

        return {
            'success': False,
            'status_code': 0,
            'wallet': wallet_address,
            'email': email,
            'username': username,
            'error': '所有重试均失败',
            'attempts': max_retries
        }

    def process_all_tokens(self, token_file="tokens.csv", report_file="report.csv", delay_between_requests=2):
        """处理所有token并记录报告"""
        print("🚀 开始处理Claim FightID")
        print("=" * 60)

        tokens_data = self.read_token_csv(token_file)
        if not tokens_data:
            print("❌ 没有可处理的token数据（或全部token为空）")
            return

        report_data = []
        success_count = 0
        fail_count = 0

        for i, token_info in enumerate(tokens_data, 1):
            print(f"\n📦 处理第 {i}/{len(tokens_data)} 个钱包")
            print("-" * 40)

            wallet_address = token_info['wallet']
            access_token = token_info['token']

            result = self.claim_fightid_for_wallet(wallet_address, access_token)

            report_row = {
                'wallet': wallet_address,
                'email': result.get('email', ''),
                'username': result.get('username', ''),
                'status': 'SUCCESS' if result['success'] else 'FAILED',
                'status_code': result.get('status_code', ''),
                'fightid_token': result.get('fightid_token', '') if result['success'] else '',
                'user_id': result.get('user_id', '') if result['success'] else '',
                'verified': result.get('verified', '') if result['success'] else '',
                'error_message': result.get('error', '') if not result['success'] else '',
                'attempts': result.get('attempts', ''),
                'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            report_data.append(report_row)

            if result['success']:
                success_count += 1
                print(f"✅ 成功处理: {wallet_address}")
            else:
                fail_count += 1
                print(f"❌ 处理失败: {wallet_address} - {result.get('error', '未知错误')}")

            if i < len(tokens_data):
                print(f"⏳ 等待 {delay_between_requests} 秒后处理下一个...")
                time.sleep(delay_between_requests)

        self.generate_report_csv(report_data, report_file)

        print("\n" + "=" * 60)
        print("📊 处理完成!")
        print(f"✅ 成功: {success_count} 个")
        print(f"❌ 失败: {fail_count} 个")
        print(f"📋 总计: {len(tokens_data)} 个")
        print(f"📄 详细报告已保存到: {report_file}")

    def generate_report_csv(self, report_data, report_file):
        """生成报告CSV文件"""
        try:
            with open(report_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'wallet', 'email', 'username', 'status', 'status_code',
                    'fightid_token', 'user_id', 'verified', 'error_message',
                    'attempts', 'processed_at'
                ]

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for row in report_data:
                    writer.writerow(row)

            print(f"💾 报告文件已生成: {report_file}")

        except Exception as e:
            print(f"❌ 生成报告文件失败: {e}")


def main():
    """主函数"""
    print("🎯 FightID Claim工具（仅处理claim-fightid）")
    print("=" * 40)

    if not os.path.exists("tokens.csv"):
        print("❌ 未找到 tokens.csv 文件")
        print("💡 请确保tokens.csv文件在当前目录下，且包含 wallet,token,更新时间 列")
        return

    claimer = FightIDClaimer()

    claimer.process_all_tokens(
        token_file="tokens.csv",
        report_file="report.csv",
        delay_between_requests=2
    )


if __name__ == "__main__":
    main()

