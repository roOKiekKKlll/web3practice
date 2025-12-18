# Fight.ID Daily Game Script
# 沙袋游戏批量处理器 (Web3 Mint)

import requests
import time
import random
import uuid
import json
import csv
import os
from datetime import datetime
import logging

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account

geth_poa_middleware = ExtraDataToPOAMiddleware

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


def call_bsc_claim(index, amount, expire_at, signature, private_key):
    """
    调用BSC链上的claim函数
    """
    if not Web3:
        print("✗ Web3库不可用，跳过链上Mint")
        return None

    print("\n" + "=" * 60)
    print("开始调用BSC链上合约")
    print("=" * 60)

    # 合约地址
    contract_address = Web3.to_checksum_address("0xD0B591751E6aa314192810471461bDE963796306")

    # 连接BSC节点
    rpc_urls = [
        'https://bsc-dataseed.binance.org/',
        'https://bsc-dataseed1.defibit.io/',
        'https://bsc-dataseed1.ninicoin.io/',
    ]

    web3 = None
    for rpc_url in rpc_urls:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 60}))
            if w3.is_connected():
                web3 = w3
                print(f"✓ 已连接BSC节点: {rpc_url}")
                break
        except:
            continue

    if not web3:
        print("✗ 无法连接到BSC节点")
        return None

    if geth_poa_middleware:
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    try:
        account = web3.eth.account.from_key(private_key)
    except:
        print("✗ 无效的私钥，无法设置账户")
        return None

    print(f"✓ 账户地址: {account.address}")

    balance = web3.eth.get_balance(account.address)
    balance_bnb = web3.from_wei(balance, 'ether')
    print(f"✓ BNB余额: {balance_bnb} BNB")

    if balance_bnb < 0.001:
        print("⚠️  警告: BNB余额较低，可能不足以支付Gas")

    contract_abi = [{
        "constant": False,
        "inputs": [
            {"name": "index", "type": "uint256"},
            {"name": "amount", "type": "uint256"},
            {"name": "expireAt", "type": "uint256"},
            {"name": "signature", "type": "bytes"}
        ],
        "name": "claim",
        "outputs": [],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }]

    contract = web3.eth.contract(address=contract_address, abi=contract_abi)

    if isinstance(signature, str):
        if signature.startswith('0x'):
            signature = signature[2:]
        signature_bytes = bytes.fromhex(signature)
    else:
        signature_bytes = signature

    print(f"\n调用参数:")
    print(f"  index: {index}")
    print(f"  amount: {amount}")
    print(f"  expireAt: {expire_at}")
    print(f"  signature: {signature[:20] if isinstance(signature, str) else '0x' + signature_bytes.hex()[:20]}...")

    try:
        print("\n正在估算Gas...")
        try:
            estimated_gas = contract.functions.claim(
                index, amount, expire_at, signature_bytes
            ).estimate_gas({'from': account.address})
            gas_limit = int(estimated_gas * 1.2)
            print(f"✓ 预估Gas: {estimated_gas}, 使用限制: {gas_limit}")
        except Exception as e:
            print(f"⚠️  Gas估算失败: {e}")
            print("使用默认Gas限制: 300000")
            gas_limit = 300000

        gas_price = web3.eth.gas_price
        gas_price_gwei = web3.from_wei(gas_price, 'gwei')
        print(f"✓ 当前Gas价格: {gas_price_gwei} Gwei")

        estimated_cost = web3.from_wei(gas_limit * gas_price, 'ether')
        print(f"✓ 预估费用: {estimated_cost} BNB")

        nonce = web3.eth.get_transaction_count(account.address)

        print("\n正在构建交易...")
        transaction = contract.functions.claim(
            index, amount, expire_at, signature_bytes
        ).build_transaction({
            'from': account.address,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': 56,
        })

        print("正在签名交易...")
        signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)

        print("正在发送交易...")
        raw_tx = getattr(signed_txn, 'raw_transaction', None) or getattr(signed_txn, 'rawTransaction', None)
        tx_hash = web3.eth.send_raw_transaction(raw_tx)
        print(f"✓ 交易已发送!")
        print(f"  交易哈希: {tx_hash.hex()}")
        print(f"  查看详情: https://bscscan.com/tx/{tx_hash.hex()}")

        print("\n等待交易确认...")
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

        if tx_receipt['status'] == 1:
            print("\n" + "=" * 60)
            print("🎉 交易成功!")
            print("=" * 60)
            print(f"区块号: {tx_receipt['blockNumber']}")
            print(f"Gas消耗: {tx_receipt['gasUsed']}")
            actual_cost = web3.from_wei(tx_receipt['gasUsed'] * gas_price, 'ether')
            print(f"实际费用: {actual_cost} BNB")
            print(f"查看交易: https://bscscan.com/tx/{tx_hash.hex()}")
            return tx_hash.hex()
        else:
            print("\n✗ 交易失败")
            return None

    except Exception as e:
        print(f"\n✗ 交易失败: {e}")
        import traceback
        traceback.print_exc()
        return None


class PunchingBagGame:
    def __init__(self, authorization_token, wallet_address="", private_key=""):
        self.authorization_token = authorization_token
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.game_session_id = None
        self.available_reward_id = None
        self.mint_data = None

        self._setup_logging()

        self.base_headers = {
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'sec-ch-ua-mobile': '?0',
            'User-Agent': random.choice(user_agents),
            'authorization': f'Bearer {authorization_token}',
            'Referer': 'https://app.fight.id',
            'sec-ch-ua-platform': '"Windows"',
            'accept': '*/*',
            'content-type': 'application/json',
            'Origin': 'https://app.fight.id'
        }

    def _setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('game.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(f"Wallet_{self.wallet_address[:8]}")

    def _generate_sentry_headers(self):
        """生成Sentry相关的头部"""
        trace_id = str(uuid.uuid4()).replace('-', '')[:32]
        return {
            'baggage': f'sentry-environment=prod,sentry-release=8170397b7005140715f0314c72eb624b4b95ed62,sentry-public_key=90dba384c939a12a890c037474951990,sentry-trace_id={trace_id},sentry-sample_rate=0.1,sentry-sampled=false',
            'sentry-trace': f'{trace_id}-{str(uuid.uuid4())[:16]}-0'
        }

    def start_game(self):
        """调用start接口开始游戏"""
        url = "https://api.fight.id/games/punching-bag-daily/start"

        headers = self.base_headers.copy()
        headers.update(self._generate_sentry_headers())

        self.logger.info("=" * 60)
        self.logger.info("🎮 1. START游戏接口")
        self.logger.info(f"   URL: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=30)

            self.logger.info(f"   状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                if result.get('success') and 'data' in result and 'sessionId' in result['data']:
                    self.game_session_id = result['data']['sessionId']
                    self.logger.info(f"✅ 游戏开始成功! Session ID: {self.game_session_id}")
                    return True
                else:
                    self.logger.error("❌ 响应格式异常")
                    return False
            elif response.status_code == 401:
                self.logger.error("❌ Token失效或认证失败")
                return False
            else:
                self.logger.error(f"❌ Start接口失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Start接口异常: {e}")
            return False

    def generate_tap_timestamps(self, count=None, duration_ms=5000):
        """生成点击时间戳列表"""
        if count is None:
            count = random.randint(18, 26)

        current_timestamp = int(time.time() * 1000)
        start_timestamp = current_timestamp - duration_ms

        timestamps = sorted([random.randint(start_timestamp, current_timestamp) for _ in range(count)])

        self.logger.info(f"⏰ 生成时间戳: 数量: {count}")
        return timestamps

    def submit_score(self):
        """调用submit接口提交分数"""
        if not self.game_session_id:
            self.logger.error("❌ 请先调用start_game开始游戏")
            return False

        url = "https://api.fight.id/games/punching-bag-daily/submit"

        tap_timestamps = self.generate_tap_timestamps()

        data = {
            "clientScore": 0,
            "gameDurationMs": 5000,
            "proofOfWork": {
                "tapTimestamps": tap_timestamps
            },
            "gameSessionId": self.game_session_id
        }

        headers = self.base_headers.copy()
        headers.update(self._generate_sentry_headers())

        self.logger.info("=" * 60)
        self.logger.info("🎯 2. SUBMIT分数接口")

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)

            self.logger.info(f"   状态码: {response.status_code}")

            if response.status_code == 201:
                result = response.json()
                if result.get('success') and 'data' in result:
                    self.available_reward_id = result['data'].get('availableRewardId')
                    score = result['data'].get('score', 0)
                    points = result['data'].get('points', 0)
                    self.logger.info(f"✅ 分数提交成功! 得分: {score}, 积分: {points}")
                    return True
                else:
                    self.logger.error("❌ 响应格式异常")
                    return False
            else:
                self.logger.error(f"❌ Submit接口失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Submit接口异常: {e}")
            return False

    def mint_api_authorize(self):
        """调用/seasons/token/mint接口获取链上Mint所需的签名数据"""
        if not self.wallet_address:
            self.logger.error("❌ 钱包地址缺失，无法进行Mint授权")
            return False

        url = "https://api.fight.id/seasons/token/mint"

        data = {
            "blockchainAddress": self.wallet_address
        }

        headers = self.base_headers.copy()
        headers.update(self._generate_sentry_headers())

        self.logger.info("=" * 60)
        self.logger.info("✨ 3. MINT授权接口 (Web2)")

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)

            self.logger.info(f"   状态码: {response.status_code}")

            if response.status_code == 201:
                result = response.json()
                if result.get('success') and 'data' in result:
                    self.mint_data = result['data']
                    self.logger.info("✅ Mint授权成功! 获取到签名数据。")
                    self.logger.info(f"   Mint金额: {self.mint_data.get('amount')}")
                    return True
                else:
                    self.logger.error("❌ Mint授权响应格式异常")
                    return False
            else:
                self.logger.error(f"❌ Mint授权接口失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Mint授权接口异常: {e}")
            return False

    def web3_mint(self):
        """调用链上合约函数进行实际Mint"""
        if not self.mint_data:
            self.logger.error("❌ 缺少Mint签名数据，无法进行链上Mint")
            return False

        if not self.private_key:
            self.logger.error("❌ 缺少私钥 (Private Key)，无法签名交易")
            return False

        try:
            season_id = self.mint_data['seasonId']
            amount = self.mint_data['amount']
            deadline = self.mint_data['deadline']
            signature = self.mint_data['signature']
        except KeyError as e:
            self.logger.error(f"❌ Mint签名数据缺少关键字段: {e}")
            return False

        self.logger.info("=" * 60)
        self.logger.info("💰 4. 执行链上 Mint (Web3)")

        tx_hash = call_bsc_claim(
            index=season_id,
            amount=amount,
            expire_at=deadline,
            signature=signature,
            private_key=self.private_key
        )

        if tx_hash:
            self.logger.info(f"✅ 链上 Mint 交易成功: {tx_hash}")
            return True
        else:
            self.logger.error("❌ 链上 Mint 交易失败")
            return False

    def run_complete_game(self):
        """运行完整的游戏流程"""
        self.logger.info(f"🚀 开始处理钱包: {self.wallet_address}")

        start_time = time.time()

        if not self.start_game():
            self.logger.error("❌ 游戏开始失败，流程终止")
            return False, "游戏开始失败"

        self.logger.info("start成功,等待6s提交分数")
        time.sleep(6)

        if not self.submit_score():
            self.logger.error("❌ 分数提交失败，流程终止")
            return False, "分数提交失败"

        wait_time = random.randint(1, 3)
        self.logger.info(f"⏳ 等待{wait_time}秒后进行Mint授权...")
        time.sleep(wait_time)

        if not self.mint_api_authorize():
            self.logger.error("❌ Mint授权失败，流程终止")
            return False, "Mint授权失败"

        if not self.web3_mint():
            self.logger.error("❌ 链上 Mint 失败，流程终止")
            return False, "链上 Mint 失败"

        execution_time = time.time() - start_time
        self.logger.info(f"✅ 游戏流程和 Mint 完成! 耗时: {execution_time:.2f}秒")
        return True, "成功"

    def reset(self):
        """重置游戏状态"""
        self.game_session_id = None
        self.available_reward_id = None
        self.mint_data = None
        self.logger.info("🔄 游戏状态已重置")


class GameBatchProcessor:
    """批量游戏处理器"""

    def __init__(self, token_file="tokens.csv", key_file="wallet.txt"):
        self.token_file = token_file
        self.key_file = key_file
        self.results_file = "game_results.csv"
        self._setup_batch_logging()

    def _setup_batch_logging(self):
        """设置批量处理的日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('game.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("BatchProcessor")

    def load_tokens_from_csv(self):
        """从tokens.csv文件加载钱包和token"""
        tokens_map = {}

        if not os.path.exists(self.token_file):
            self.logger.error(f"❌ Token文件 {self.token_file} 不存在")
            return tokens_map

        try:
            with open(self.token_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    wallet = row.get('wallet', '').strip().lower()
                    token = row.get('token', '').strip()
                    if wallet and token:
                        tokens_map[wallet] = token

            self.logger.info(f"✅ 从 {self.token_file} 加载了 {len(tokens_map)} 个有效Token")
            return tokens_map

        except Exception as e:
            self.logger.error(f"❌ 加载token文件失败: {e}")
            return {}

    def load_private_keys(self):
        """从wallets.txt文件加载私钥"""
        private_keys = []
        if not os.path.exists(self.key_file):
            self.logger.error(f"❌ 私钥文件 {self.key_file} 不存在")
            return private_keys

        try:
            with open(self.key_file, 'r', encoding='utf-8') as f:
                for line in f:
                    key = line.strip()
                    if key:
                        private_keys.append(key)

            self.logger.info(f"✅ 从 {self.key_file} 加载了 {len(private_keys)} 个私钥")
            return private_keys

        except Exception as e:
            self.logger.error(f"❌ 加载私钥文件失败: {e}")
            return []

    def save_game_result(self, wallet, success, message, execution_time):
        """保存游戏结果到CSV文件"""
        try:
            file_exists = os.path.exists(self.results_file)

            with open(self.results_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['wallet', 'success', 'message', 'execution_time', 'timestamp'])

                writer.writerow([
                    wallet,
                    success,
                    message,
                    f"{execution_time:.2f}s",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ])

        except Exception as e:
            self.logger.error(f"❌ 保存游戏结果失败: {e}")

    def process_all_wallets(self, delay_between_wallets=5):
        """处理所有钱包的游戏任务"""
        self.logger.info("🚀 开始批量处理钱包游戏任务 (包含链上Mint)")

        if not Web3:
            self.logger.error("致命错误: Web3库未安装或导入失败，无法进行链上Mint。流程终止。")
            return

        private_keys = self.load_private_keys()
        tokens_map = self.load_tokens_from_csv()

        if not private_keys:
            self.logger.error("❌ 没有可用的私钥数据")
            return
        if not tokens_map:
            self.logger.error("❌ 没有可用的Token数据")
            return

        wallets_to_process = []
        for private_key in private_keys:
            try:
                account = Account.from_key(private_key)
                wallet_address = account.address.lower()

                if wallet_address in tokens_map:
                    wallets_to_process.append({
                        'wallet': account.address,
                        'token': tokens_map[wallet_address],
                        'private_key': private_key
                    })
                else:
                    self.logger.warning(f"⚠️ 地址 {account.address} 在 tokens.csv 中未找到匹配的 Token，跳过。")
            except Exception as e:
                self.logger.error(f"❌ 私钥解析失败或Web3错误: {e}")

        if not wallets_to_process:
            self.logger.error("❌ 经过匹配，没有可处理的钱包/Token对")
            return

        self.logger.info(f"📋 找到 {len(wallets_to_process)} 个钱包/Token/私钥对需要处理")

        successful_count = 0
        failed_count = 0

        for i, data in enumerate(wallets_to_process, 1):
            wallet = data['wallet']
            token = data['token']
            private_key = data['private_key']

            self.logger.info(f"\n🎯 处理第 {i}/{len(wallets_to_process)} 个钱包: {wallet}")

            start_time = time.time()

            try:
                game = PunchingBagGame(token, wallet, private_key)
                success, message = game.run_complete_game()
                execution_time = time.time() - start_time
                self.save_game_result(wallet, success, message, execution_time)

                if success:
                    successful_count += 1
                    self.logger.info(f"✅ 钱包 {wallet} 处理成功")
                else:
                    failed_count += 1
                    self.logger.error(f"❌ 钱包 {wallet} 处理失败: {message}")

            except Exception as e:
                execution_time = time.time() - start_time
                self.save_game_result(wallet, False, str(e), execution_time)
                failed_count += 1
                self.logger.error(f"❌ 钱包 {wallet} 处理异常: {e}")

            if i < len(wallets_to_process):
                self.logger.info(f"⏳ 等待 {delay_between_wallets} 秒后处理下一个钱包...")
                time.sleep(delay_between_wallets)

        self.logger.info("\n" + "=" * 80)
        self.logger.info("📊 批量处理完成!")
        self.logger.info(f"✅ 成功: {successful_count} 个钱包")
        self.logger.info(f"❌ 失败: {failed_count} 个钱包")
        self.logger.info(f"💾 详细结果已保存到: {self.results_file}")

        return {
            'successful': successful_count,
            'failed': failed_count,
            'total': len(wallets_to_process)
        }


def main():
    """主函数 - 批量处理模式"""
    print("🎮 FIGHT.iD 沙袋游戏批量处理器 (Web3 Mint)")
    print("=" * 60)

    token_file = "tokens.csv"
    key_file = "wallet.txt"
    if not os.path.exists(token_file):
        print(f"❌ 未找到 {token_file} 文件")
        return
    if not os.path.exists(key_file):
        print(f"❌ 未找到 {key_file} 文件")
        return

    if not Web3:
        print("❌ 缺少 Web3.py 库。请安装: pip install web3")
        return

    processor = GameBatchProcessor(token_file, key_file)
    result = processor.process_all_wallets(delay_between_wallets=5)

    print(f"\n🎯 处理完成! 成功: {result['successful']}, 失败: {result['failed']}")


def test_single_wallet():
    """测试单个钱包（调试用）"""
    # 从环境变量或配置文件读取
    wallet = os.getenv("TEST_WALLET_ADDRESS", "0xYOUR_WALLET_ADDRESS")
    token = os.getenv("TEST_TOKEN", "YOUR_ACCESS_TOKEN")
    private_key = os.getenv("TEST_PRIVATE_KEY", "YOUR_PRIVATE_KEY")

    print(f"🔧 测试单个钱包: {wallet}")
    game = PunchingBagGame(token, wallet, private_key)
    success, message = game.run_complete_game()

    if success:
        print("🎉 测试成功!")
    else:
        print(f"❌ 测试失败: {message}")


if __name__ == "__main__":
    main()

