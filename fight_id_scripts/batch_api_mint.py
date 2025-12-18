"""
Fight.id API Mint调用脚本 + BSC合约调用 (批量版本)
从 wallet.txt 读取私钥，从 tokens.csv 读取对应的 token
"""

import requests
import json
import time
import csv
from web3 import Web3

try:
    from web3.middleware import ExtraDataToPOAMiddleware

    geth_poa_middleware = ExtraDataToPOAMiddleware
except ImportError:
    try:
        from web3.middleware import geth_poa_middleware
    except ImportError:
        geth_poa_middleware = None


def call_mint_api(blockchain_address: str, authorization: str, max_retries: int = 3):
    """
    调用Fight.id的mint API（带重试机制）
    """
    url = "https://api.fight.id/seasons/token/mint"

    headers = {
        'sec-ch-ua-platform': '"macOS"',
        'authorization': f'Bearer {authorization}' if not authorization.startswith('Bearer') else authorization,
        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'content-type': 'application/json',
        "origin": "https://app.fight.id",
    }

    data = {
        "blockchainAddress": blockchain_address
    }

    print(f"正在调用API: {url}")
    print(f"钱包地址: {blockchain_address}")
    print(f"Authorization: {authorization[:20]}..." if len(authorization) > 20 else f"Authorization: {authorization}")
    print()

    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                print(f"\n第 {attempt}/{max_retries} 次尝试...")

            response = requests.post(url, headers=headers, json=data, timeout=30)

            print(f"状态码: {response.status_code}")

            if response.status_code == 201:
                print("✓ 调用成功!")
                print("\n响应数据:")
                print("=" * 60)

                try:
                    response_json = response.json()
                    print(json.dumps(response_json, indent=2, ensure_ascii=False))
                    return response_json
                except:
                    print(response.text)
                    return response.text

            else:
                print("✗ 调用失败")
                print(f"响应内容: {response.text}")

                if attempt < max_retries:
                    wait_time = attempt * 2
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"\n已达到最大重试次数({max_retries})，放弃重试")
                    return None

        except requests.exceptions.Timeout:
            print(f"✗ 请求超时")
            if attempt < max_retries:
                wait_time = attempt * 2
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"\n已达到最大重试次数({max_retries})，放弃重试")
                return None

        except Exception as e:
            print(f"✗ 请求失败: {e}")
            if attempt < max_retries:
                wait_time = attempt * 2
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"\n已达到最大重试次数({max_retries})，放弃重试")
                return None

    return None


def read_private_keys(file_path="wallet.txt"):
    """从文件读取所有私钥"""
    try:
        with open(file_path, 'r') as f:
            private_keys = []
            for line in f:
                private_key = line.strip()
                if private_key:
                    if not private_key.startswith('0x'):
                        private_key = '0x' + private_key
                    private_keys.append(private_key)
            return private_keys
    except FileNotFoundError:
        print(f"✗ 未找到文件: {file_path}")
        return []
    except Exception as e:
        print(f"✗ 读取私钥失败: {e}")
        return []


def load_tokens_mapping(file_path="tokens.csv"):
    """从 CSV 文件加载钱包地址到 token 的映射"""
    tokens_map = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                wallet = row['wallet'].strip().lower()
                token = row['token'].strip()
                tokens_map[wallet] = token

        print(f"✓ 成功加载 {len(tokens_map)} 个钱包的 token 映射")
        return tokens_map
    except FileNotFoundError:
        print(f"✗ 未找到文件: {file_path}")
        return {}
    except Exception as e:
        print(f"✗ 读取 tokens.csv 失败: {e}")
        return {}


def get_address_from_private_key(private_key):
    """从私钥推导出钱包地址"""
    try:
        account = Web3().eth.account.from_key(private_key)
        return account.address.lower()
    except Exception as e:
        print(f"✗ 从私钥推导地址失败: {e}")
        return None


def call_bsc_claim(index, amount, expire_at, signature, private_key):
    """调用BSC链上的claim函数"""
    print("\n" + "=" * 60)
    print("开始调用BSC链上合约")
    print("=" * 60)

    contract_address = Web3.to_checksum_address("0xD0B591751E6aa314192810471461bDE963796306")

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

    account = web3.eth.account.from_key(private_key)
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


def process_single_wallet(private_key, authorization, wallet_address):
    """处理单个钱包的完整流程"""
    print("\n" + "=" * 80)
    print(f"开始处理钱包: {wallet_address}")
    print("=" * 80)

    print("\n【步骤1】调用API获取claim参数")
    print("-" * 60)
    api_result = call_mint_api(wallet_address, authorization)

    if not api_result:
        print("\n✗ API调用失败，跳过此钱包")
        return False

    if not isinstance(api_result, dict) or 'data' not in api_result:
        print("\n✗ API返回格式错误")
        return False

    data = api_result['data']

    index = data.get('seasonId')
    amount = data.get('amount')
    expire_at = data.get('deadline')
    signature = data.get('signature')

    print(f"\n✓ 成功获取claim参数:")
    print(f"  index (seasonId): {index}")
    print(f"  amount: {amount}")
    print(f"  expireAt (deadline): {expire_at}")
    print(f"  signature: {signature[:20]}..." if signature else "  signature: None")

    if not all([index is not None, amount is not None, expire_at is not None, signature]):
        print("\n✗ 参数不完整，跳过此钱包")
        return False

    print("\n【步骤2】调用BSC链上合约")
    print("-" * 60)

    tx_hash = call_bsc_claim(index, amount, expire_at, signature, private_key)

    if tx_hash:
        print("\n" + "=" * 60)
        print(f"✓✓✓ 钱包 {wallet_address} 处理成功 ✓✓✓")
        print("=" * 60)
        print(f"交易哈希: {tx_hash}")
        print(f"查看交易: https://bscscan.com/tx/{tx_hash}")
        return True
    else:
        print(f"\n✗ 钱包 {wallet_address} 合约调用失败")
        return False


def main():
    """主函数 - 批量处理"""

    print("=" * 80)
    print("Fight.id 批量Mint + Claim 脚本")
    print("=" * 80)
    print()

    print("【阶段1】读取私钥文件")
    print("-" * 80)
    private_keys = read_private_keys("wallet.txt")

    if not private_keys:
        print("✗ 未读取到任何私钥，程序终止")
        return

    print(f"✓ 成功读取 {len(private_keys)} 个私钥")

    print("\n【阶段2】加载 tokens.csv 映射")
    print("-" * 80)
    tokens_map = load_tokens_mapping("tokens.csv")

    if not tokens_map:
        print("✗ 未能加载 token 映射，程序终止")
        return

    print("\n【阶段3】开始批量处理")
    print("-" * 80)

    success_count = 0
    fail_count = 0
    skip_count = 0

    results = []

    for idx, private_key in enumerate(private_keys, 1):
        print(f"\n\n{'=' * 80}")
        print(f"处理进度: {idx}/{len(private_keys)}")
        print(f"{'=' * 80}")

        wallet_address = get_address_from_private_key(private_key)
        if not wallet_address:
            print(f"✗ 无法从私钥推导地址，跳过")
            skip_count += 1
            results.append({
                'index': idx,
                'wallet': 'Unknown',
                'status': 'SKIP',
                'reason': '无法推导地址'
            })
            continue

        authorization = tokens_map.get(wallet_address)
        if not authorization:
            print(f"✗ 钱包 {wallet_address} 在 tokens.csv 中未找到对应的 token，跳过")
            skip_count += 1
            results.append({
                'index': idx,
                'wallet': wallet_address,
                'status': 'SKIP',
                'reason': '未找到token'
            })
            continue

        try:
            success = process_single_wallet(private_key, authorization, wallet_address)
            if success:
                success_count += 1
                results.append({
                    'index': idx,
                    'wallet': wallet_address,
                    'status': 'SUCCESS',
                    'reason': ''
                })
            else:
                fail_count += 1
                results.append({
                    'index': idx,
                    'wallet': wallet_address,
                    'status': 'FAIL',
                    'reason': 'API或合约调用失败'
                })
        except Exception as e:
            print(f"\n✗ 处理钱包 {wallet_address} 时发生异常: {e}")
            fail_count += 1
            results.append({
                'index': idx,
                'wallet': wallet_address,
                'status': 'ERROR',
                'reason': str(e)
            })

        if idx < len(private_keys):
            wait_time = 3
            print(f"\n⏳ 等待 {wait_time} 秒后处理下一个钱包...")
            time.sleep(wait_time)

    print("\n\n" + "=" * 80)
    print("📊 批量处理完成 - 最终统计")
    print("=" * 80)
    print(f"总计钱包数: {len(private_keys)}")
    print(f"✓ 成功: {success_count}")
    print(f"✗ 失败: {fail_count}")
    print(f"⊘ 跳过: {skip_count}")
    print()

    print("详细结果:")
    print("-" * 80)
    for result in results:
        status_symbol = {
            'SUCCESS': '✓',
            'FAIL': '✗',
            'SKIP': '⊘',
            'ERROR': '⚠'
        }.get(result['status'], '?')

        reason_text = f" - {result['reason']}" if result['reason'] else ""
        print(
            f"{status_symbol} #{result['index']} {result['wallet'][:10]}...{result['wallet'][-8:]}: {result['status']}{reason_text}")


if __name__ == "__main__":
    main()

