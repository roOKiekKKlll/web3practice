"""
BSC 链合约调用脚本
功能: Mint NFT + 质押
"""

import time
import requests
from web3 import Web3
from eth_account import Account

# API 配置
WHITELIST_API = "https://rwa.sharex.network/api/nfts/whitelist/essentia/"

# ========== 配置 ==========
BSC_RPC = "https://bsc-dataseed.binance.org/"
# 备用 RPC
# BSC_RPC = "https://bsc-dataseed1.defibit.io/"
# BSC_RPC = "https://bsc-dataseed1.ninicoin.io/"

# 合约地址
MINT_CONTRACT = "0x28e3889A3bc57D4421a5041E85Df8b516Ab683F8"
STAKE_CONTRACT = "0xC7e54532ea427b7Bcf682dc0BEF24CD1338b3026"

# 固定参数
TOKEN_ID = 0
AMOUNT = 1

# Mint 合约 ABI (仅包含需要的函数)
MINT_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "operator", "type": "address"},
            {"internalType": "bool", "name": "approved", "type": "bool"}
        ],
        "name": "setApprovalForAll",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "account", "type": "address"},
            {"internalType": "address", "name": "operator", "type": "address"}
        ],
        "name": "isApprovedForAll",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Stake 合约 ABI (仅包含需要的函数)
STAKE_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "stake",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


def load_wallets(file_path: str) -> list:
    """从文件加载钱包私钥"""
    wallets = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # 确保私钥格式正确
                if not line.startswith('0x'):
                    line = '0x' + line
                wallets.append(line)
    return wallets


def get_gas_price(w3: Web3) -> int:
    """获取当前 gas 价格，添加一点缓冲"""
    gas_price = w3.eth.gas_price
    # 增加 10% 作为缓冲
    return int(gas_price * 1.1)


def wait_for_tx(w3: Web3, tx_hash: str, timeout: int = 120) -> dict:
    """等待交易确认"""
    print(f"    等待交易确认: {tx_hash}")
    start = time.time()
    while True:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt is not None:
                return receipt
        except Exception:
            pass
        
        if time.time() - start > timeout:
            raise TimeoutError(f"交易超时: {tx_hash}")
        time.sleep(2)


def set_whitelist_api(address: str) -> bool:
    """调用 API 设置白名单"""
    print(f"  [Whitelist API] 设置白名单...")
    
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'cache-control': 'no-cache, no-store, must-revalidate',
        'content-type': 'application/json',
        'origin': 'https://rwa.sharex.network',
        'pragma': 'no-cache',
        'referer': 'https://rwa.sharex.network/sharex-keys-series/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }
    
    payload = {"account": address.lower()}
    
    try:
        response = requests.post(WHITELIST_API, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"    白名单设置成功 ✓")
                print(f"    TX: {data.get('transactionHash', 'N/A')}")
                print(f"    当前 Essentia: {data.get('data', {}).get('currentEssentiaAmount', 'N/A')}")
                return True
            else:
                print(f"    API 返回失败: {data}")
                return False
        else:
            print(f"    API 请求失败，状态码: {response.status_code}")
            print(f"    响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"    API 请求异常: {e}")
        return False


def mint_nft(w3: Web3, account, mint_contract, token_id: int, amount: int) -> str:
    """调用 mint 函数"""
    print(f"  [Mint] tokenId={token_id}, amount={amount}")
    
    # 构建交易
    tx = mint_contract.functions.mint(token_id, amount).build_transaction({
        'from': account.address,
        'gas': 200000,
        'gasPrice': get_gas_price(w3),
        'nonce': w3.eth.get_transaction_count(account.address),
        'chainId': 56  # BSC 主网
    })
    
    # 签名并发送
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return w3.to_hex(tx_hash)


def approve_for_staking(w3: Web3, account, mint_contract, stake_contract_address: str) -> str:
    """授权质押合约操作 NFT"""
    # 检查是否已授权
    is_approved = mint_contract.functions.isApprovedForAll(
        account.address, 
        stake_contract_address
    ).call()
    
    if is_approved:
        print("  [Approve] 已授权，跳过")
        return None
    
    print(f"  [Approve] 授权质押合约...")
    
    tx = mint_contract.functions.setApprovalForAll(
        stake_contract_address, 
        True
    ).build_transaction({
        'from': account.address,
        'gas': 100000,
        'gasPrice': get_gas_price(w3),
        'nonce': w3.eth.get_transaction_count(account.address),
        'chainId': 56
    })
    
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return w3.to_hex(tx_hash)


def stake_nft(w3: Web3, account, stake_contract, token_id: int, amount: int) -> str:
    """调用 stake 函数"""
    print(f"  [Stake] tokenId={token_id}, amount={amount}")
    
    tx = stake_contract.functions.stake(token_id, amount).build_transaction({
        'from': account.address,
        'gas': 200000,
        'gasPrice': get_gas_price(w3),
        'nonce': w3.eth.get_transaction_count(account.address),
        'chainId': 56
    })
    
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return w3.to_hex(tx_hash)


def process_wallet(w3: Web3, private_key: str, mint_contract, stake_contract) -> dict:
    """处理单个钱包：mint + stake"""
    account = Account.from_key(private_key)
    address = account.address
    result = {
        'address': address,
        'mint_tx': None,
        'approve_tx': None,
        'stake_tx': None,
        'success': False,
        'error': None
    }
    
    print(f"\n{'='*60}")
    print(f"处理钱包: {address}")
    
    # 检查余额
    balance = w3.eth.get_balance(address)
    balance_bnb = w3.from_wei(balance, 'ether')
    print(f"  BNB 余额: {balance_bnb:.6f}")
    
    if balance < w3.to_wei(0.001, 'ether'):
        result['error'] = "BNB 余额不足"
        print(f"  错误: {result['error']}")
        return result
    
    try:
        # Step 0: 设置白名单
        if not set_whitelist_api(address):
            result['error'] = "白名单设置失败"
            print(f"  错误: {result['error']}")
            return result
        
        # 等待链上白名单生效
        print("  等待白名单生效 (3秒)...")
        time.sleep(3)
        
        # Step 1: Mint
        mint_tx = mint_nft(w3, account, mint_contract, TOKEN_ID, AMOUNT)
        result['mint_tx'] = mint_tx
        print(f"    Mint TX: {mint_tx}")
        
        receipt = wait_for_tx(w3, mint_tx)
        if receipt['status'] != 1:
            raise Exception("Mint 交易失败")
        print("    Mint 成功 ✓")
        
        # Step 2: Approve (如果需要)
        approve_tx = approve_for_staking(w3, account, mint_contract, STAKE_CONTRACT)
        if approve_tx:
            result['approve_tx'] = approve_tx
            print(f"    Approve TX: {approve_tx}")
            
            receipt = wait_for_tx(w3, approve_tx)
            if receipt['status'] != 1:
                raise Exception("Approve 交易失败")
            print("    Approve 成功 ✓")
        
        # Step 3: Stake
        stake_tx = stake_nft(w3, account, stake_contract, TOKEN_ID, AMOUNT)
        result['stake_tx'] = stake_tx
        print(f"    Stake TX: {stake_tx}")
        
        receipt = wait_for_tx(w3, stake_tx)
        if receipt['status'] != 1:
            raise Exception("Stake 交易失败")
        print("    Stake 成功 ✓")
        
        result['success'] = True
        print(f"  钱包处理完成 ✓")
        
    except Exception as e:
        result['error'] = str(e)
        print(f"  错误: {e}")
    
    return result


def main():
    print("=" * 60)
    print("BSC Mint + Stake 脚本")
    print("=" * 60)
    
    # 连接到 BSC
    w3 = Web3(Web3.HTTPProvider(BSC_RPC))
    if not w3.is_connected():
        print("无法连接到 BSC 网络!")
        return
    print(f"已连接到 BSC，当前区块: {w3.eth.block_number}")
    
    # 初始化合约
    mint_contract = w3.eth.contract(
        address=Web3.to_checksum_address(MINT_CONTRACT),
        abi=MINT_ABI
    )
    stake_contract = w3.eth.contract(
        address=Web3.to_checksum_address(STAKE_CONTRACT),
        abi=STAKE_ABI
    )
    
    # 加载钱包
    wallets = load_wallets('wallet.txt')
    print(f"加载了 {len(wallets)} 个钱包")
    
    if not wallets:
        print("没有找到钱包!")
        return
    
    # 处理每个钱包
    results = []
    success_count = 0
    fail_count = 0
    
    for i, private_key in enumerate(wallets, 1):
        print(f"\n[{i}/{len(wallets)}]")
        result = process_wallet(w3, private_key, mint_contract, stake_contract)
        results.append(result)
        
        if result['success']:
            success_count += 1
        else:
            fail_count += 1
        
        # 钱包之间稍作延迟
        if i < len(wallets):
            print("  等待 3 秒后处理下一个钱包...")
            time.sleep(3)
    
    # 打印总结
    print("\n" + "=" * 60)
    print("执行总结")
    print("=" * 60)
    print(f"总钱包数: {len(wallets)}")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    
    # 打印失败详情
    if fail_count > 0:
        print("\n失败钱包:")
        for r in results:
            if not r['success']:
                print(f"  {r['address']}: {r['error']}")
    
    # 保存结果到文件
    with open('mint_stake_results.csv', 'w', encoding='utf-8') as f:
        f.write("address,mint_tx,approve_tx,stake_tx,success,error\n")
        for r in results:
            f.write(f"{r['address']},{r['mint_tx'] or ''},{r['approve_tx'] or ''},{r['stake_tx'] or ''},{r['success']},{r['error'] or ''}\n")
    print("\n结果已保存到 mint_stake_results.csv")


if __name__ == "__main__":
    main()
