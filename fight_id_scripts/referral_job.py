# Fight.ID Referral Job Script
# 批量注册并使用推荐码

import requests
import time
import random
import uuid
import csv
import os
import hashlib
import string
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
except ImportError:
    print("❌ 缺少EVM依赖库，请安装: pip install eth-account")
    exit(1)

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
    def __init__(self, referral_file="referral_info_main.csv"):
        self.session = requests.Session()
        self.referral_file = referral_file

        # 推荐码使用次数范围配置
        self._MIN_REFERRAL_USES = 8
        self._MAX_REFERRAL_USES = 15

        self._ensure_referral_file_schema()

        self._referral_data = self._load_referral_data()
        self._referral_codes = list(self._referral_data.keys())
        self._referral_index = 0

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

    def _ensure_referral_file_schema(self):
        """检查并确保 referral_info_main.csv 包含 'referral_count' 列"""
        required_field = 'referral_count'

        if not os.path.exists(self.referral_file):
            return

        try:
            with open(self.referral_file, 'r', newline='', encoding='utf-8') as f:
                reader_dict = csv.DictReader(f)
                original_fieldnames = reader_dict.fieldnames
                data_rows = list(reader_dict)

            if not original_fieldnames or required_field in original_fieldnames:
                return

            print(f"⚠️ 文件 {self.referral_file} 缺少 '{required_field}' 列。正在初始化...")

            new_fieldnames = original_fieldnames.copy()
            new_fieldnames.append(required_field)

            for row in data_rows:
                row[required_field] = '0'

            with open(self.referral_file, 'w', newline='', encoding='utf-8') as f_write:
                writer = csv.DictWriter(f_write, fieldnames=new_fieldnames)
                writer.writeheader()
                writer.writerows(data_rows)

            print(f"✅ 文件 {self.referral_file} 已添加 '{required_field}' 列并初始化为 0。")

        except Exception as e:
            print(f"❌ 确保文件结构失败: {e}")

    def _load_referral_data(self):
        """加载 referral_info_main.csv 文件中的推荐码数据"""
        referral_data = {}

        if not os.path.exists(self.referral_file):
            return referral_data

        try:
            with open(self.referral_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    code = row.get('referralCode', '').strip()
                    if not code:
                        continue

                    try:
                        count = int(row.get('referral_count', 0))
                    except ValueError:
                        count = 0

                    if count >= self._MIN_REFERRAL_USES:
                        target = count
                        status = "已达跳过点"
                    else:
                        target = random.randint(self._MIN_REFERRAL_USES, self._MAX_REFERRAL_USES)
                        status = "进行中"

                    referral_data[code] = {
                        'wallet': row.get('wallet', ''),
                        'count': count,
                        'target_count': target,
                        'status': status
                    }
                print(f"✅ 已加载 {len(referral_data)} 个有效推荐码进行轮询。")
                print(f"    - 随机上限范围: {self._MIN_REFERRAL_USES} 到 {self._MAX_REFERRAL_USES} 次。")
        except Exception as e:
            print(f"❌ 加载 Referral 文件失败: {e}")

        return referral_data

    def _update_referral_count(self, referral_code, increment=1):
        """更新推荐码计数"""
        if referral_code not in self._referral_data:
            return

        self._referral_data[referral_code]['count'] += increment
        current_count = self._referral_data[referral_code]['count']
        target_count = self._referral_data[referral_code]['target_count']

        if current_count >= target_count:
            print(f"🎉 推荐码 {referral_code} 计数达到目标 {target_count} 次，本次会话将停止使用。")
            if current_count >= self._MIN_REFERRAL_USES:
                self._referral_data[referral_code]['status'] = "已达跳过点"
        else:
            print(f"💾 推荐码 {referral_code} 计数已更新到 {current_count}/{target_count}")

        updated_rows = []
        try:
            with open(self.referral_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                existing_data = list(reader)

            for row in existing_data:
                current_code_in_row = row.get('referralCode', '').strip()
                if current_code_in_row == referral_code:
                    row['referral_count'] = str(current_count)
                updated_rows.append(row)

            with open(self.referral_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(updated_rows)

        except Exception as e:
            print(f"❌ 更新 Referral 文件失败: {e}")

    def _get_next_available_referral_code(self):
        """轮询获取下一个可用的推荐码"""
        start_index = self._referral_index

        if not self._referral_codes:
            return None

        while True:
            code = self._referral_codes[self._referral_index]
            data = self._referral_data[code]
            current_count = data['count']
            target_count = data['target_count']

            if current_count < target_count:
                self._referral_index = (self._referral_index + 1) % len(self._referral_codes)
                return code

            self._referral_index = (self._referral_index + 1) % len(self._referral_codes)

            if self._referral_index == start_index:
                print("⚠️ 所有推荐码均已达到或超过本次会话的目标使用限制！")
                return None

    def _generate_random_username(self, length_range=(10, 20)):
        min_len, max_len = length_range
        length = random.randint(min_len, max_len)
        characters = string.ascii_letters + string.digits
        username = ''.join(random.choice(characters) for _ in range(length))
        return username

    def _generate_dynamic_headers(self):
        trace_id = str(uuid.uuid4()).replace('-', '')[:32]
        span_id = str(uuid.uuid4())[:16]

        return {
            'baggage': f'sentry-environment=prod,sentry-release=b8554ef5f6b72af778dbccc86df2f236042f15f3,sentry-public_key=90dba384c939a12a890c037474951990,sentry-trace_id={trace_id},sentry-sample_rate=0.1,sentry-sampled=false',
            'sentry-trace': f'{trace_id}-{span_id}-0'
        }

    def _load_wallet_private_keys(self, file_path="referral_wallet.txt"):
        """从文件加载所有钱包私钥"""
        try:
            with open(file_path, 'r') as f:
                private_keys = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            print(f"✅ 从 {file_path} 加载了 {len(private_keys)} 个私钥")
            return private_keys
        except FileNotFoundError:
            print(f"❌ 钱包文件 {file_path} 未找到")
            return []

    def _private_key_to_address(self, private_key_hex):
        try:
            account = Account.from_key(private_key_hex)
            return account.address
        except Exception:
            return None

    def _generate_evm_signature(self, message, private_key_hex):
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
        except Exception:
            address = self._private_key_to_address(private_key_hex)
            return {
                'address': address,
                'signature': '0x' + hashlib.sha256((message + private_key_hex).encode()).hexdigest()[:130],
                'success': False
            }

    def step1_get_nonce(self, max_retries=3):
        url = "https://api.fight.id/auth/siwa"
        for attempt in range(max_retries):
            try:
                dynamic_headers = self._generate_dynamic_headers()
                headers = {**self.base_headers, **dynamic_headers}
                response = self.session.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    result = response.json()
                    return {'success': True, 'data': result.get('data'), 'response': result}
                elif response.status_code == 429:
                    wait_time = (2 ** attempt) + random.uniform(0.1, 0.5)
                    time.sleep(wait_time)
                    continue

                if attempt < max_retries - 1:
                    wait_time = 1 + attempt
                    time.sleep(wait_time)

            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
        return {'success': False, 'error': '所有重试均失败'}

    def step2_callback(self, nonce_data, private_key, max_retries=3):
        url = "https://api.fight.id/auth/siwa/callback"
        message = "Sign in to get access to FIGHT.iD"
        sign_result = self._generate_evm_signature(message, private_key)

        if not sign_result or not sign_result['success']:
            return {'success': False, 'error': '签名生成失败'}

        wallet_address = sign_result['address']
        signature = sign_result['signature']
        timestamp = int(time.time() * 1000)

        request_data = {
            "input": {"nonce": nonce_data.get('nonce', ''), "nonceId": nonce_data.get('nonceId', ''),
                      "resources": nonce_data.get('resources', []),
                      "statement": nonce_data.get('statement', 'Sign in to get access to FIGHT.iD')},
            "output": {"address": wallet_address, "signature": signature, "nonce": nonce_data.get('nonce', ''),
                       "message": message, "fullMessage": message, "domain": "app.fight.id", "statement": message,
                       "email": "", "timestamp": timestamp}
        }

        for attempt in range(max_retries):
            try:
                dynamic_headers = self._generate_dynamic_headers()
                headers = {**self.base_headers, **dynamic_headers}
                response = self.session.post(url, headers=headers, json=request_data, timeout=15)

                if response.status_code == 201:
                    result = response.json()
                    access_token = result.get('data', {}).get('accessToken')
                    if access_token:
                        return {'success': True, 'access_token': access_token, 'address': wallet_address,
                                'status_code': 201}
                    else:
                        return {'success': False, 'error': 'No access token received'}

                if attempt < max_retries - 1:
                    wait_time = 1 + attempt
                    time.sleep(wait_time)

            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
        return {'success': False, 'error': '所有重试均失败'}

    def step3_claim_fightid(self, access_token, wallet_address, max_retries=3):
        url = "https://api.fight.id/user/claim-fightid"

        referral_code = self._get_next_available_referral_code()
        if not referral_code:
            print("❌ 无法获取可用的推荐码，跳过注册。")
            return {'success': False, 'error': 'No available referral codes'}

        email = f"{wallet_address.lower()}@temp.wallet"
        username = self._generate_random_username()
        referral_source = ""

        target_count = self._referral_data[referral_code]['target_count']

        request_data = {
            "email": email,
            "username": username,
            "referralCode": referral_code,
            "referralSource": referral_source
        }

        print(f"📧 邮箱: {email}")
        print(f"👤 用户名: {username}")
        print(f"🎯 推荐码: {referral_code} (目标: {target_count}, 当前: {self._referral_data[referral_code]['count']})")

        claim_headers = {
            'accept': '*/*',
            'accept-language': 'ja',
            'authorization': f'Bearer {access_token}',
            'baggage': f'sentry-environment=prod,sentry-release=322e03722b5b3b9cb6009bd85565a5034efe634b,sentry-public_key=90dba384c939a12a890c037474951990,sentry-trace_id={str(uuid.uuid4()).replace("-", "")[:32]},sentry-sample_rate=0.1,sentry-sampled=false',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://app.fight.id',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'sentry-trace': f'{str(uuid.uuid4()).replace("-", "")[:32]}-{str(uuid.uuid4())[:16]}-0',
            'user-agent': self.base_headers['User-Agent']
        }

        for attempt in range(max_retries):
            try:
                response = self.session.post(url, headers=claim_headers, json=request_data, timeout=15)
                print(f"📥 状态码: {response.status_code}")

                if response.status_code == 201:
                    result = response.json()
                    print("✅ Claim FightID 成功!")

                    fightid_token = result.get('data', {}).get('accessToken')
                    returned_username = result.get('data', {}).get('username')

                    if fightid_token:
                        self._update_referral_count(referral_code, 1)

                        return {
                            'success': True,
                            'fightid_token': fightid_token,
                            'username': returned_username,
                            'referral_code_used': referral_code
                        }
                    else:
                        return {'success': False, 'error': 'No fightid token received'}

                elif response.status_code == 400:
                    error_msg = response.json().get('message', '请求参数错误或用户已存在')
                    print(f"❌ 400 错误: {error_msg}")
                    if "already in use" in error_msg:
                        return {'success': False, 'error': f'Bad request: {error_msg}', 'status_code': 400}

                if attempt < max_retries - 1:
                    time.sleep(1)
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue

        return {'success': False, 'error': '所有重试均失败'}

    def process_single_wallet(self, private_key):
        wallet_address = self._private_key_to_address(private_key)

        print(f"\n🎯 处理钱包: {private_key[:10]}...{wallet_address[-6:]}")
        print("-" * 50)

        if not self._get_next_available_referral_code():
            print("⚠️ 当前无可用推荐码，停止该钱包流程。")
            return {'success': False, 'address': wallet_address, 'error': 'No available referral codes to use'}

        step1_result = self.step1_get_nonce()
        if not step1_result['success'] or not step1_result.get('data'):
            print("❌ 第一步失败，跳过该钱包")
            return None

        nonce_data = step1_result['data']

        step2_result = self.step2_callback(nonce_data, private_key)

        if not step2_result['success']:
            print(f"❌ 第二步失败，跳过该钱包")
            return None

        access_token = step2_result['access_token']
        wallet_address = step2_result['address']

        print(f"\n🚀 开始第三步：Claim FightID")
        print("-" * 30)
        step3_result = self.step3_claim_fightid(access_token, wallet_address)

        if step3_result['success']:
            print(f"✅ 完整流程处理成功!")
            return {'success': True, 'address': wallet_address, 'username': step3_result['username'],
                    'referral_code_used': step3_result['referral_code_used']}
        else:
            print(f"❌ 第三步失败: {step3_result.get('error', '未知错误')}")
            return {'success': False, 'address': wallet_address, 'error': step3_result.get('error', '未知错误')}

    def batch_process_wallets(self, wallet_file="referral_wallet.txt", max_workers=5, delay_between_tasks=0.5):
        """批量处理所有钱包"""
        print("🚀 开始批量并发处理钱包（仅记录推荐码邀请数）")
        print("=" * 60)

        private_keys = self._load_wallet_private_keys(wallet_file)
        if not private_keys:
            print("❌ 未找到可用的私钥")
            return

        print(f"📋 找到 {len(private_keys)} 个钱包，最大并发数: {max_workers}")

        successful_count = 0
        failed_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_key = {executor.submit(self.process_single_wallet, key): key for key in private_keys}

            for i, future in enumerate(as_completed(future_to_key), 1):
                result = future.result()

                print(f"\n[Progress] {i}/{len(private_keys)} 个任务完成.")

                if result and result['success']:
                    successful_count += 1
                else:
                    failed_count += 1

                time.sleep(delay_between_tasks)

        print("\n" + "=" * 60)
        print("📊 批量处理完成!")
        print(f"✅ 成功邀请: {successful_count} 次")
        print(f"❌ 失败/跳过: {failed_count} 次")
        print(f"💾 推荐码计数已更新到 {self.referral_file}")

        return {'successful_count': successful_count, 'failed_count': failed_count}


def main_batch_wallets():
    """批量处理所有钱包"""
    print("🔐 批量并发处理模式")
    client = SIWAClient(referral_file="referral_info_main.csv")

    MAX_CONCURRENT_WORKERS = 5

    result = client.batch_process_wallets(
        wallet_file="referral_wallet.txt",
        max_workers=MAX_CONCURRENT_WORKERS,
        delay_between_tasks=0.5
    )
    print(f"\n🎯 最终统计! 成功邀请: {result['successful_count']}, 失败/跳过: {result['failed_count']}")


if __name__ == "__main__":
    wallet_file = "referral_wallet.txt"
    referral_file = "referral_info_main.csv"

    if os.path.exists(wallet_file) and os.path.exists(referral_file):
        print("📁 检测到钱包和推荐码文件，开始批量并发处理...")
        main_batch_wallets()
    else:
        print(f"❌ 未找到所需文件：请确保 {wallet_file} 和 {referral_file} 文件存在。")

        if not os.path.exists(wallet_file):
            print(f"💡 正在创建 {wallet_file} 示例文件...")
            with open(wallet_file, "w") as f:
                f.write("# 请将您的EVM私钥按行添加到此文件\n")
                f.write("# 0x你的私钥1\n")
                f.write("# 0x你的私钥2\n")

        if not os.path.exists(referral_file):
            print(f"💡 正在创建 {referral_file} 示例文件...")
            with open(referral_file, "w", newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['wallet', 'referralCode'])
                writer.writerow(['0xabc...', 'CODE123'])
                writer.writerow(['0xdef...', 'CODE456'])
            print(f"📝 已创建示例文件：{wallet_file} 和 {referral_file}")

