# Fight.ID Batch Login Script
# 批量登录获取Token

import requests
import time
import random
import uuid
import json
import csv
import os
from datetime import datetime
from eth_account import Account
from eth_account.messages import encode_defunct
import hashlib

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


class SIWAClient:
    def __init__(self, wallet_private_key=None):
        self.session = requests.Session()
        self.wallet_private_key = wallet_private_key
        self.tokens_file = "tokens.csv"

        # 基础头部配置
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
        self._init_csv_file()

    def _init_csv_file(self):
        """初始化CSV文件"""
        if not os.path.exists(self.tokens_file):
            with open(self.tokens_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['wallet', 'token', '更新时间'])

    def _load_existing_tokens(self):
        """加载现有的token记录"""
        existing_tokens = {}
        if os.path.exists(self.tokens_file):
            try:
                with open(self.tokens_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['wallet']:
                            existing_tokens[row['wallet'].lower()] = {
                                'token': row.get('token', ''),
                                '更新时间': row.get('更新时间', '')
                            }
                print(f"✅ 已加载 {len(existing_tokens)} 条现有token记录")
            except Exception as e:
                print(f"❌ 加载现有token记录失败: {e}")
        return existing_tokens

    def _update_token_record(self, wallet_address, access_token=None):
        """更新token记录"""
        existing_tokens = self._load_existing_tokens()
        wallet_lower = wallet_address.lower()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if wallet_lower in existing_tokens:
            if access_token:
                existing_tokens[wallet_lower]['token'] = access_token
                existing_tokens[wallet_lower]['更新时间'] = current_time
                print(f"🔄 更新钱包 {wallet_address} 的token记录")
            else:
                existing_tokens[wallet_lower]['token'] = ''
                existing_tokens[wallet_lower]['更新时间'] = current_time
                print(f"🔄 清空钱包 {wallet_address} 的token记录（登录失败）")
        else:
            existing_tokens[wallet_lower] = {
                'token': access_token if access_token else '',
                '更新时间': current_time
            }
            print(f"🆕 新增钱包 {wallet_address} 的记录")

        self._write_tokens_to_csv(existing_tokens)
        return True

    def _write_tokens_to_csv(self, tokens_dict):
        """将token字典写入CSV文件"""
        try:
            with open(self.tokens_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['wallet', 'token', '更新时间'])
                for wallet in sorted(tokens_dict.keys()):
                    token_data = tokens_dict[wallet]
                    writer.writerow([wallet, token_data['token'], token_data['更新时间']])
            print(f"💾 Token记录已保存到 {self.tokens_file}")
        except Exception as e:
            print(f"❌ 保存token记录失败: {e}")

    def _generate_dynamic_headers(self):
        """生成动态的sentry头部"""
        trace_id = str(uuid.uuid4()).replace('-', '')[:32]
        span_id = str(uuid.uuid4())[:16]

        return {
            'baggage': f'sentry-environment=prod,sentry-release=b8554ef5f6b72af778dbccc86df2f236042f15f3,sentry-public_key=90dba384c939a12a890c037474951990,sentry-trace_id={trace_id},sentry-sample_rate=0.1,sentry-sampled=false',
            'sentry-trace': f'{trace_id}-{span_id}-0'
        }

    def _load_wallet_private_keys(self, file_path="wallet.txt"):
        """从文件加载所有钱包私钥"""
        try:
            with open(file_path, 'r') as f:
                private_keys = [line.strip() for line in f if line.strip()]
            print(f"✅ 从 {file_path} 加载了 {len(private_keys)} 个私钥")
            return private_keys
        except FileNotFoundError:
            print(f"❌ 钱包文件 {file_path} 未找到")
            return []

    def _private_key_to_address(self, private_key_hex):
        """将EVM私钥转换为地址"""
        try:
            account = Account.from_key(private_key_hex)
            return account.address
        except Exception as e:
            print(f"❌ 地址生成失败: {e}")
            return None

    def _generate_evm_signature(self, message, private_key_hex):
        """生成EVM兼容的签名"""
        try:
            account = Account.from_key(private_key_hex)
            message_text = f"Sign in to get access to FIGHT.iD"
            encoded_message = encode_defunct(text=message_text)
            signed_message = Account.sign_message(encoded_message, private_key_hex)

            return {
                'address': account.address,
                'signature': signed_message.signature.hex(),
                'success': True
            }
        except Exception as e:
            print(f"❌ EVM签名生成失败: {e}")
            address = self._private_key_to_address(private_key_hex)
            return {
                'address': address,
                'signature': '0x' + hashlib.sha256((message + private_key_hex).encode()).hexdigest()[:130],
                'success': False
            }

    def step1_get_nonce(self, max_retries=3):
        """第一步：获取nonce数据"""
        url = "https://api.fight.id/auth/siwa"

        for attempt in range(max_retries):
            try:
                dynamic_headers = self._generate_dynamic_headers()
                headers = {**self.base_headers, **dynamic_headers}

                print(f"🔄 第一步：获取nonce (尝试 {attempt + 1}/{max_retries})")

                response = self.session.get(url, headers=headers, timeout=10)
                print(f"📥 状态码: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    print("✅ Nonce获取成功!")
                    return {
                        'success': True,
                        'data': result.get('data'),
                        'response': result
                    }
                elif response.status_code == 429:
                    wait_time = (2 ** attempt) + random.uniform(0.1, 0.5)
                    print(f"⏳ 频率限制，等待 {wait_time:.2f}秒")
                    time.sleep(wait_time)
                    continue

                if attempt < max_retries - 1:
                    wait_time = 1 + attempt
                    print(f"⏳ 等待 {wait_time}秒后重试...")
                    time.sleep(wait_time)

            except Exception as e:
                print(f"❌ 请求异常: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue

        return {'success': False, 'error': '所有重试均失败'}

    def step2_callback(self, nonce_data, private_key, max_retries=3):
        """第二步：执行回调认证"""
        url = "https://api.fight.id/auth/siwa/callback"

        message = "Sign in to get access to FIGHT.iD"
        sign_result = self._generate_evm_signature(message, private_key)

        if not sign_result:
            return {'success': False, 'error': '签名生成失败'}

        wallet_address = sign_result['address']
        signature = sign_result['signature']

        timestamp = int(time.time() * 1000)

        request_data = {
            "input": {
                "nonce": nonce_data.get('nonce', ''),
                "nonceId": nonce_data.get('nonceId', ''),
                "resources": nonce_data.get('resources', []),
                "statement": nonce_data.get('statement', 'Sign in to get access to FIGHT.iD')
            },
            "output": {
                "address": wallet_address,
                "signature": signature,
                "nonce": nonce_data.get('nonce', ''),
                "message": message,
                "fullMessage": message,
                "domain": "app.fight.id",
                "statement": message,
                "email": "",
                "timestamp": timestamp
            }
        }

        print(f"📍 钱包地址: {wallet_address}")

        for attempt in range(max_retries):
            try:
                dynamic_headers = self._generate_dynamic_headers()
                headers = {**self.base_headers, **dynamic_headers}

                print(f"🔄 第二步：回调认证 (尝试 {attempt + 1}/{max_retries})")

                response = self.session.post(url, headers=headers, json=request_data, timeout=15)
                print(f"📥 状态码: {response.status_code}")

                if response.status_code == 201:
                    result = response.json()
                    print("✅ 回调认证成功!")

                    access_token = result.get('data', {}).get('accessToken')
                    if access_token:
                        self._update_token_record(wallet_address, access_token)
                        return {
                            'success': True,
                            'access_token': access_token,
                            'address': wallet_address,
                            'response': result,
                            'status_code': 201
                        }
                    else:
                        print("❌ 未获取到accessToken")
                        self._update_token_record(wallet_address, None)
                        return {
                            'success': False,
                            'error': 'No access token received',
                            'response': result
                        }
                else:
                    print(f"❌ HTTP错误: {response.status_code}")
                    self._update_token_record(wallet_address, None)

                if attempt < max_retries - 1:
                    wait_time = 1 + attempt
                    print(f"⏳ 等待 {wait_time}秒后重试...")
                    time.sleep(wait_time)

            except Exception as e:
                print(f"❌ 请求异常: {e}")
                self._update_token_record(wallet_address, None)
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue

        return {'success': False, 'error': '所有重试均失败'}

    def process_single_wallet(self, private_key):
        """处理单个钱包的完整流程"""
        print(f"\n🎯 处理钱包: {private_key[:20]}...")
        print("-" * 50)

        step1_result = self.step1_get_nonce()
        if not step1_result['success']:
            print("❌ 第一步失败，跳过该钱包")
            wallet_address = self._private_key_to_address(private_key)
            if wallet_address:
                self._update_token_record(wallet_address, None)
            return None

        nonce_data = step1_result['data']
        if not nonce_data:
            print("❌ 未获取到nonce数据，跳过该钱包")
            wallet_address = self._private_key_to_address(private_key)
            if wallet_address:
                self._update_token_record(wallet_address, None)
            return None

        step2_result = self.step2_callback(nonce_data, private_key)

        if step2_result['success']:
            print(f"✅ 钱包处理完成: {step2_result['address']}")
            return step2_result
        else:
            print(f"❌ 钱包处理失败: {step2_result.get('error', '未知错误')}")
            return None

    def batch_process_wallets(self, wallet_file="wallet.txt", delay_between_wallets=3):
        """批量处理所有钱包"""
        print("🚀 开始批量处理钱包")
        print("=" * 60)

        private_keys = self._load_wallet_private_keys(wallet_file)
        if not private_keys:
            print("❌ 未找到可用的私钥")
            return

        print(f"📋 找到 {len(private_keys)} 个钱包")

        existing_tokens = self._load_existing_tokens()
        for private_key in private_keys:
            wallet_address = self._private_key_to_address(private_key)
            if wallet_address and wallet_address.lower() not in existing_tokens:
                self._update_token_record(wallet_address, None)

        successful_tokens = []
        failed_wallets = []

        for i, private_key in enumerate(private_keys, 1):
            print(f"\n📦 处理第 {i}/{len(private_keys)} 个钱包")
            print("=" * 40)

            result = self.process_single_wallet(private_key)

            if result and result['success']:
                successful_tokens.append({
                    'address': result['address'],
                    'access_token': result['access_token']
                })
            else:
                failed_wallets.append(private_key[:20] + "...")

            if i < len(private_keys):
                print(f"⏳ 等待 {delay_between_wallets} 秒后处理下一个钱包...")
                time.sleep(delay_between_wallets)

        print("\n" + "=" * 60)
        print("📊 批量处理完成!")
        print(f"✅ 成功: {len(successful_tokens)} 个钱包")
        print(f"❌ 失败: {len(failed_wallets)} 个钱包")
        print(f"💾 Token记录已更新到 {self.tokens_file}")

        return {
            'successful': successful_tokens,
            'failed': failed_wallets
        }


def main_single_wallet():
    """处理单个钱包（测试用）"""
    print("🔧 单钱包测试模式")
    # 从环境变量读取测试私钥
    example_private_key = os.getenv("TEST_PRIVATE_KEY", "")
    if not example_private_key:
        print("❌ 请设置环境变量 TEST_PRIVATE_KEY")
        return
    
    client = SIWAClient()
    result = client.process_single_wallet(example_private_key)
    if result and result['success']:
        print(f"🎉 认证成功! Address: {result['address']}")
    else:
        print("❌ 认证失败")


def main_batch_wallets():
    """批量处理所有钱包"""
    print("🔐 批量处理模式")
    client = SIWAClient()
    result = client.batch_process_wallets("wallet.txt", delay_between_wallets=2)
    print(f"\n🎯 处理完成! 成功: {len(result['successful'])}, 失败: {len(result['failed'])}")


if __name__ == "__main__":
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct

        print("✅ EVM依赖库已安装")
    except ImportError:
        print("❌ 缺少EVM依赖库，请安装: pip install eth-account")
        exit(1)

    wallet_file = "wallet.txt"
    if os.path.exists(wallet_file):
        print("📁 检测到钱包文件，开始批量处理...")
        main_batch_wallets()
    else:
        print("❌ 未找到wallet.txt文件")
        print("💡 请创建wallet.txt文件，每行一个EVM私钥")
        with open("wallet_example.txt", "w") as f:
            f.write("# 请将您的EVM私钥按行添加到此文件\n")
            f.write("# 0x你的私钥1\n")
            f.write("# 0x你的私钥2\n")
        print("📝 已创建示例文件: wallet_example.txt")

