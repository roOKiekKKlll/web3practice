# Fight.ID Distribute BNB Script
# 批量分发 BNB Gas

import csv
import time
import random
from web3 import Web3
from typing import List, Dict, Optional
import os

# ==================== PoA 中间件兼容性导入 ====================
try:
    from web3.middleware import ExtraDataToPOAMiddleware
    poa_middleware = ExtraDataToPOAMiddleware
    print("✓ 使用新版 PoA 中间件: ExtraDataToPOAMiddleware")
except ImportError:
    try:
        from web3.middleware import geth_poa_middleware
        poa_middleware = geth_poa_middleware
        print("✓ 使用旧版 PoA 中间件: geth_poa_middleware")
    except ImportError:
        poa_middleware = None
        print("✗ 警告: 无法导入任何 PoA 中间件，可能影响 BSC 连接稳定性。")

# ==================== 配置区域 ====================
# 1. BNB Smart Chain (BSC) RPC 节点
RPC_URLS = [
    'https://bsc-dataseed.binance.org/',
    'https://bsc-dataseed1.defibit.io/',
    'https://bsc-dataseed1.ninicoin.io/',
]

# 2. 文件名配置
MAIN_WALLET_FILE = "main_wallet.txt"
TOKENS_CSV_FILE = "tokens.csv"
OUTPUT_CSV_FILE = "gas_distribution_report.csv"

# 3. Gas 分发金额配置 (以 BNB 为单位)
MIN_AMOUNT_BNB = 0.00007
MAX_AMOUNT_BNB = 0.00011

# 4. 延迟配置
DELAY_BETWEEN_TX = 0.5


# ==================== 工具函数 ====================

def load_main_private_key(file_path: str) -> Optional[str]:
    """从文件读取主钱包私钥"""
    try:
        with open(file_path, 'r') as f:
            private_key = f.read().strip()
            if not private_key:
                print(f"✗ 错误: 文件 {file_path} 内容为空。")
                return None
            if not private_key.startswith('0x'):
                private_key = '0x' + private_key
            print(f"✓ 成功读取主钱包私钥。")
            return private_key
    except FileNotFoundError:
        print(f"✗ 错误: 未找到主钱包文件: {file_path}")
        return None
    except Exception as e:
        print(f"✗ 错误: 读取主钱包私钥失败: {e}")
        return None


def load_target_addresses(file_path: str) -> List[str]:
    """从 tokens.csv 文件加载子钱包地址"""
    addresses = set()
    try:
        with open(file_path, 'r', newline='') as f:
            reader = csv.reader(f)
            try:
                next(reader)
            except StopIteration:
                print(f"✗ 警告: 文件 {file_path} 为空。")
                return []

            for row in reader:
                if row and row[0].strip():
                    address = row[0].strip()
                    try:
                        checksum_address = Web3.to_checksum_address(address)
                        addresses.add(checksum_address)
                    except ValueError:
                        print(f"✗ 警告: 发现无效地址 '{address}'，已跳过。")
                        continue

    except FileNotFoundError:
        print(f"✗ 错误: 未找到子钱包文件: {file_path}")
        return []
    except Exception as e:
        print(f"✗ 错误: 读取子钱包地址失败: {e}")
        return []

    print(f"✓ 成功从 {file_path} 加载 {len(addresses)} 个子钱包地址。")
    return list(addresses)


def connect_bsc(rpc_urls: List[str]) -> Optional[Web3]:
    """连接BSC节点"""
    print("【步骤1】尝试连接 BSC 节点...")
    for rpc_url in rpc_urls:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 30}))
            if w3.is_connected():
                if poa_middleware:
                    w3.middleware_onion.inject(poa_middleware, layer=0)
                print(f"✓ 成功连接BSC节点: {rpc_url}")
                return w3
        except:
            continue
    print("✗ 无法连接到任何BSC节点，请检查网络或RPC配置。")
    return None


def write_report(results: List[Dict[str, str]], output_file: str):
    """将分发结果写入 CSV 报告"""
    print(f"\n正在生成报告文件: {output_file}...")
    try:
        with open(output_file, 'w', newline='') as f:
            fieldnames = ['target_wallet', 'amount_bnb', 'status', 'tx_hash', 'error']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print("✓ 报告生成完毕。")
    except Exception as e:
        print(f"✗ 报告写入失败: {e}")


# ==================== 核心分发逻辑 ====================

def distribute_gas():
    """执行Gas分发的主逻辑"""

    print("=" * 60)
    print("BNB Gas 批量分发脚本启动 (随机金额)")
    print("=" * 60)

    # 1. 准备数据
    main_pk = load_main_private_key(MAIN_WALLET_FILE)
    if not main_pk:
        return

    target_addresses = load_target_addresses(TOKENS_CSV_FILE)
    if not target_addresses:
        return

    w3 = connect_bsc(RPC_URLS)
    if not w3:
        return

    # 2. 设置主钱包账户
    try:
        main_account = w3.eth.account.from_key(main_pk)
        sender_address = main_account.address
        print(f"✓ 主钱包地址: {sender_address}")
    except Exception as e:
        print(f"✗ 错误: 私钥格式无效，无法创建账户。{e}")
        return

    # 3. 检查主钱包余额
    total_required_bnb_max = MAX_AMOUNT_BNB * len(target_addresses)

    try:
        current_balance = w3.eth.get_balance(sender_address)
        current_balance_bnb = w3.from_wei(current_balance, 'ether')

        print(f"✓ 当前主钱包 BNB 余额: {current_balance_bnb:.4f} BNB")
        print(f"✓ 每个子钱包分发金额范围: {MIN_AMOUNT_BNB} - {MAX_AMOUNT_BNB} BNB")
        print(f"✓ 目标分发子钱包数量: {len(target_addresses)} 个")

        total_estimate = total_required_bnb_max + (len(target_addresses) * 0.0005)

        if current_balance_bnb < total_estimate:
            print(f"✗ 警告: 主钱包余额可能不足以完成所有分发和Gas费。预计需要约 {total_estimate:.4f} BNB。")
    except Exception as e:
        print(f"✗ 错误: 无法获取主钱包余额: {e}")
        return

    # 4. 开始批量分发
    print("\n" + "=" * 60)
    print("【步骤2】开始批量分发 Gas")
    print("=" * 60)

    results = []

    nonce = w3.eth.get_transaction_count(sender_address)
    gas_price = w3.eth.gas_price
    gas_limit = 25000

    gas_price_gwei = w3.from_wei(gas_price, 'gwei')
    estimated_tx_cost = w3.from_wei(gas_limit * gas_price, 'ether')

    print(f"  > Gas Price: {gas_price_gwei} Gwei")
    print(f"  > 每笔交易估计Gas费: {estimated_tx_cost:.6f} BNB")
    print("-" * 60)

    for i, recipient_address in enumerate(target_addresses):

        amount_bnb_to_send = random.uniform(MIN_AMOUNT_BNB, MAX_AMOUNT_BNB)
        amount_wei = w3.to_wei(amount_bnb_to_send, 'ether')

        current_result = {
            'target_wallet': recipient_address,
            'amount_bnb': f"{amount_bnb_to_send:.8f}",
            'status': 'Failed',
            'tx_hash': '',
            'error': ''
        }

        print(f"[{i + 1}/{len(target_addresses)}] 发送到 {recipient_address} (金额: {amount_bnb_to_send:.8f} BNB)...")

        if recipient_address == sender_address:
            current_result['status'] = 'Skipped'
            current_result['error'] = 'SelfTransfer'
            print("  - 警告: 目标地址是主钱包自己，跳过。")
            results.append(current_result)
            continue

        try:
            tx = {
                'from': sender_address,
                'to': recipient_address,
                'value': amount_wei,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': 56
            }

            signed_tx = w3.eth.account.sign_transaction(tx, private_key=main_pk)

            raw_tx = getattr(signed_tx, 'raw_transaction', None) or getattr(signed_tx, 'rawTransaction', None)

            if not raw_tx:
                raise AttributeError("SignedTransaction object is missing 'raw_transaction' attribute.")

            tx_hash = w3.eth.send_raw_transaction(raw_tx)

            print(f"  - ✓ 交易已发送! Hash: {tx_hash.hex()[:10]}...")
            print(f"  - 详情: https://bscscan.com/tx/{tx_hash.hex()}")

            nonce += 1

            current_result['status'] = 'Success'
            current_result['tx_hash'] = tx_hash.hex()

        except Exception as e:
            error_msg = str(e)

            if "nonce too low" in error_msg.lower():
                print("  - ✗ 错误: Nonce 过低，尝试重新获取 Nonce。")
                nonce = w3.eth.get_transaction_count(sender_address)
                current_result['error'] = 'NonceError'
            elif "insufficient funds" in error_msg.lower():
                print("  - ✗ 错误: 主钱包余额不足以支付当前交易的 Gas 或金额。")
                current_result['error'] = 'InsufficientFunds'
                break
            elif "raw_transaction" in error_msg:
                print("  - ✗ 错误: web3.py 属性访问失败。请尝试升级或降级 web3.py 版本。")
                current_result['error'] = 'AttributeError'

            else:
                print(f"  - ✗ 交易失败: {error_msg}")
                current_result['error'] = error_msg[:100]

        results.append(current_result)

        time.sleep(DELAY_BETWEEN_TX)

    # 5. 总结和报告
    print("\n" + "=" * 60)
    print("Gas 分发任务完成")
    print("=" * 60)
    write_report(results, OUTPUT_CSV_FILE)

    success_count = sum(1 for r in results if r['status'] == 'Success')
    print(f"总计尝试分发: {len(target_addresses)} 笔")
    print(f"成功发送交易: {success_count} 笔 (注意：发送成功不代表链上确认成功)")
    print("请查看 gas_distribution_report.csv 文件获取详细状态。")


if __name__ == "__main__":
    # 演示用的文件创建
    if not os.path.exists(MAIN_WALLET_FILE):
        with open(MAIN_WALLET_FILE, "w") as f:
            f.write("# 请将您的主钱包私钥填入此文件（移除此注释行）\n")
            f.write("# YOUR_MAIN_WALLET_PRIVATE_KEY_HERE\n")
        print(f"\n[INFO] 请将您的主钱包私钥填入 {MAIN_WALLET_FILE} 文件。")

    if not os.path.exists(TOKENS_CSV_FILE):
        with open(TOKENS_CSV_FILE, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['wallet', 'token', 'update_time'])
            writer.writerow(['0x0000000000000000000000000000000000000001', 'token1', '2025-01-01'])
            writer.writerow(['0x0000000000000000000000000000000000000002', 'token2', '2025-01-01'])
        print(f"[INFO] 请将您的子钱包地址填入 {TOKENS_CSV_FILE} 文件的 'wallet' 列。")

    distribute_gas()

