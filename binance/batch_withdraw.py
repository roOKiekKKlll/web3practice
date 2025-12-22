"""
Binance 批量提现脚本
支持提现到多个不同地址，支持多种币种和网络
支持代理连接（用于 IP 白名单）
"""

import csv
import time
import hmac
import hashlib
import requests
from datetime import datetime
from typing import Optional
from config import API_KEY, API_SECRET, WHITELIST_PROXY

# Binance API 基础URL
BASE_URL = "https://api.binance.com"

# 提现地址文件
WITHDRAW_FILE = "withdraw_addresses.csv"
# 结果日志文件
RESULT_FILE = "withdraw_results.csv"


def parse_proxy(proxy_str: str) -> dict:
    """
    解析代理字符串为 requests 格式
    
    Args:
        proxy_str: 代理字符串，格式: IP:PORT:USERNAME:PASSWORD
    
    Returns:
        requests 代理字典
    """
    if not proxy_str:
        return None
    
    parts = proxy_str.split(":")
    if len(parts) == 4:
        ip, port, username, password = parts
        proxy_url = f"http://{username}:{password}@{ip}:{port}"
    elif len(parts) == 2:
        ip, port = parts
        proxy_url = f"http://{ip}:{port}"
    else:
        print(f"代理格式错误: {proxy_str}")
        return None
    
    return {
        "http": proxy_url,
        "https": proxy_url
    }


# 解析代理配置
PROXIES = parse_proxy(WHITELIST_PROXY)
if PROXIES:
    print(f"✓ 已启用代理: {WHITELIST_PROXY.split(':')[0]}:{WHITELIST_PROXY.split(':')[1]}")
else:
    print("⚠ 未配置代理，将直接连接")


def get_timestamp():
    """获取当前时间戳（毫秒）"""
    return int(time.time() * 1000)


def test_proxy_connection() -> bool:
    """
    测试代理连接是否正常
    
    Returns:
        代理是否可用
    """
    print("\n测试代理连接中...")
    try:
        # 测试获取当前 IP
        response = requests.get(
            "https://api.ipify.org?format=json",
            proxies=PROXIES,
            timeout=10
        )
        if response.status_code == 200:
            current_ip = response.json().get("ip", "未知")
            print(f"✓ 代理连接成功")
            print(f"  当前出口 IP: {current_ip}")
            return True
        else:
            print(f"✗ 代理连接失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 代理连接错误: {e}")
        return False


def create_signature(params: dict) -> str:
    """创建 API 签名"""
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(
        API_SECRET.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return signature


def get_headers():
    """获取请求头"""
    return {
        "X-MBX-APIKEY": API_KEY,
        "Content-Type": "application/x-www-form-urlencoded"
    }


def get_spot_balance(asset: str = None) -> dict:
    """
    获取现货账户余额
    
    Args:
        asset: 指定币种，如 'USDT'、'BNB' 等。为 None 时返回所有余额
    
    Returns:
        现货账户余额信息
    """
    endpoint = "/api/v3/account"
    params = {
        "timestamp": get_timestamp(),
        "recvWindow": 5000
    }
    params["signature"] = create_signature(params)
    
    response = requests.get(
        f"{BASE_URL}{endpoint}",
        params=params,
        headers=get_headers(),
        proxies=PROXIES,
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        balances = {b["asset"]: {"free": float(b["free"]), "locked": float(b["locked"])} 
                   for b in data["balances"] if float(b["free"]) > 0 or float(b["locked"]) > 0}
        if asset:
            return balances.get(asset, {"free": 0, "locked": 0})
        return balances
    else:
        print(f"获取现货余额失败: {response.text}")
        return {}


def get_funding_balance(asset: str = None) -> dict:
    """
    获取资金账户余额（用于充值/提现/C2C）
    
    Args:
        asset: 指定币种
    
    Returns:
        资金账户余额信息
    """
    endpoint = "/sapi/v1/asset/get-funding-asset"
    params = {
        "timestamp": get_timestamp(),
        "recvWindow": 5000
    }
    if asset:
        params["asset"] = asset
    
    params["signature"] = create_signature(params)
    
    response = requests.post(
        f"{BASE_URL}{endpoint}",
        data=params,
        headers=get_headers(),
        proxies=PROXIES,
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        balances = {b["asset"]: {"free": float(b["free"]), "locked": float(b["locked"]), "freeze": float(b["freeze"])} 
                   for b in data if float(b["free"]) > 0 or float(b["locked"]) > 0 or float(b["freeze"]) > 0}
        return balances
    else:
        print(f"获取资金账户余额失败: {response.text}")
        return {}


def get_earn_balance() -> dict:
    """
    获取理财账户余额（活期+定期）
    
    Returns:
        理财账户余额信息
    """
    balances = {}
    
    # 活期理财
    endpoint_flexible = "/sapi/v1/simple-earn/flexible/position"
    params = {
        "timestamp": get_timestamp(),
        "recvWindow": 5000,
        "size": 100
    }
    params["signature"] = create_signature(params)
    
    response = requests.get(
        f"{BASE_URL}{endpoint_flexible}",
        params=params,
        headers=get_headers(),
        proxies=PROXIES,
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        for item in data.get("rows", []):
            asset = item.get("asset")
            amount = float(item.get("totalAmount", 0))
            if amount > 0:
                if asset not in balances:
                    balances[asset] = {"flexible": 0, "locked": 0}
                balances[asset]["flexible"] = amount
    
    # 定期理财
    endpoint_locked = "/sapi/v1/simple-earn/locked/position"
    params = {
        "timestamp": get_timestamp(),
        "recvWindow": 5000,
        "size": 100
    }
    params["signature"] = create_signature(params)
    
    response = requests.get(
        f"{BASE_URL}{endpoint_locked}",
        params=params,
        headers=get_headers(),
        proxies=PROXIES,
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        for item in data.get("rows", []):
            asset = item.get("asset")
            amount = float(item.get("amount", 0))
            if amount > 0:
                if asset not in balances:
                    balances[asset] = {"flexible": 0, "locked": 0}
                balances[asset]["locked"] = amount
    
    return balances


def get_all_balances() -> dict:
    """
    获取所有账户的余额汇总
    
    Returns:
        所有账户余额信息
    """
    return {
        "spot": get_spot_balance(),
        "funding": get_funding_balance(),
        "earn": get_earn_balance()
    }


def get_withdraw_history(coin: str = None, limit: int = 10) -> list:
    """
    获取提现历史
    
    Args:
        coin: 币种
        limit: 返回数量
    
    Returns:
        提现历史列表
    """
    endpoint = "/sapi/v1/capital/withdraw/history"
    params = {
        "timestamp": get_timestamp(),
        "recvWindow": 5000,
        "limit": limit
    }
    if coin:
        params["coin"] = coin
    
    params["signature"] = create_signature(params)
    
    response = requests.get(
        f"{BASE_URL}{endpoint}",
        params=params,
        headers=get_headers(),
        proxies=PROXIES,
        timeout=30
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"获取提现历史失败: {response.text}")
        return []


def get_coin_info(coin: str = None) -> list:
    """
    获取币种信息（包括支持的网络）
    
    Args:
        coin: 币种名称
    
    Returns:
        币种信息列表
    """
    endpoint = "/sapi/v1/capital/config/getall"
    params = {
        "timestamp": get_timestamp(),
        "recvWindow": 5000
    }
    params["signature"] = create_signature(params)
    
    response = requests.get(
        f"{BASE_URL}{endpoint}",
        params=params,
        headers=get_headers(),
        proxies=PROXIES,
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        if coin:
            for item in data:
                if item["coin"] == coin:
                    return item
            return None
        return data
    else:
        print(f"获取币种信息失败: {response.text}")
        return []


def withdraw(
    coin: str,
    address: str,
    amount: float,
    network: str = None,
    address_tag: str = None,
    wallet_type: int = 0
) -> dict:
    """
    执行提现操作
    
    Args:
        coin: 币种，如 'USDT'、'BNB' 等
        address: 提现地址
        amount: 提现数量
        network: 网络类型，如 'BSC'、'ETH'、'TRX' 等
        address_tag: 地址标签（某些币种需要，如 XRP 的 memo）
        wallet_type: 钱包类型。0-现货钱包，1-资金钱包
    
    Returns:
        提现结果
    """
    endpoint = "/sapi/v1/capital/withdraw/apply"
    
    params = {
        "coin": coin,
        "address": address,
        "amount": amount,
        "timestamp": get_timestamp(),
        "recvWindow": 5000,
        "walletType": wallet_type
    }
    
    if network:
        params["network"] = network
    
    if address_tag:
        params["addressTag"] = address_tag
    
    params["signature"] = create_signature(params)
    
    response = requests.post(
        f"{BASE_URL}{endpoint}",
        data=params,
        headers=get_headers(),
        proxies=PROXIES,
        timeout=30
    )
    
    result = {
        "success": response.status_code == 200,
        "coin": coin,
        "address": address,
        "amount": amount,
        "network": network,
        "response": response.json() if response.status_code == 200 else response.text
    }
    
    return result


def load_withdraw_addresses(filename: str = WITHDRAW_FILE) -> list:
    """
    从 CSV 文件加载提现地址列表
    
    CSV 格式: coin,address,amount,network,address_tag
    
    Args:
        filename: CSV 文件路径
    
    Returns:
        提现地址列表
    """
    addresses = []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                addresses.append({
                    "coin": row.get("coin", "").strip().upper(),
                    "address": row.get("address", "").strip(),
                    "amount": float(row.get("amount", 0)),
                    "network": row.get("network", "").strip().upper() if row.get("network") else None,
                    "address_tag": row.get("address_tag", "").strip() if row.get("address_tag") else None
                })
    except FileNotFoundError:
        print(f"错误: 找不到文件 {filename}")
        print("请创建 withdraw_addresses.csv 文件，格式如下:")
        print("coin,address,amount,network,address_tag")
        print("USDT,0x1234...abcd,100,BSC,")
    except Exception as e:
        print(f"读取文件错误: {e}")
    
    return addresses


def save_result(results: list, filename: str = RESULT_FILE):
    """
    保存提现结果到 CSV 文件
    
    Args:
        results: 提现结果列表
        filename: 输出文件名
    """
    with open(filename, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["timestamp", "coin", "address", "amount", "network", "success", "response"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "coin": result.get("coin"),
                "address": result.get("address"),
                "amount": result.get("amount"),
                "network": result.get("network"),
                "success": result.get("success"),
                "response": str(result.get("response"))
            })
    
    print(f"\n结果已保存到 {filename}")


def batch_withdraw(
    addresses: list,
    delay: float = 1.0,
    dry_run: bool = False
) -> list:
    """
    批量执行提现
    
    Args:
        addresses: 提现地址列表
        delay: 每次提现之间的延迟（秒）
        dry_run: 如果为 True，只显示将要执行的操作，不实际执行
    
    Returns:
        提现结果列表
    """
    results = []
    total = len(addresses)
    
    print(f"\n{'='*60}")
    print(f"批量提现任务")
    print(f"{'='*60}")
    print(f"总计 {total} 个提现任务")
    
    if dry_run:
        print("\n[模拟运行模式] - 不会实际执行提现\n")
    
    for i, addr in enumerate(addresses, 1):
        print(f"\n[{i}/{total}] 处理中...")
        print(f"  币种: {addr['coin']}")
        print(f"  地址: {addr['address'][:20]}...{addr['address'][-10:]}")
        print(f"  数量: {addr['amount']}")
        print(f"  网络: {addr['network'] or '默认'}")
        
        if dry_run:
            result = {
                "success": True,
                "coin": addr["coin"],
                "address": addr["address"],
                "amount": addr["amount"],
                "network": addr["network"],
                "response": "[DRY RUN] 模拟成功"
            }
        else:
            result = withdraw(
                coin=addr["coin"],
                address=addr["address"],
                amount=addr["amount"],
                network=addr["network"],
                address_tag=addr["address_tag"]
            )
        
        results.append(result)
        
        if result["success"]:
            print(f"  状态: ✓ 成功")
            if not dry_run:
                print(f"  提现ID: {result['response'].get('id', 'N/A')}")
        else:
            print(f"  状态: ✗ 失败")
            print(f"  错误: {result['response']}")
        
        # 延迟，避免请求过快
        if i < total:
            time.sleep(delay)
    
    # 统计结果
    success_count = sum(1 for r in results if r["success"])
    fail_count = total - success_count
    
    print(f"\n{'='*60}")
    print(f"批量提现完成")
    print(f"{'='*60}")
    print(f"成功: {success_count}/{total}")
    print(f"失败: {fail_count}/{total}")
    
    return results


def show_balance(account_type: str = "all"):
    """
    显示账户余额
    
    Args:
        account_type: 账户类型 - "spot"(现货), "funding"(资金), "earn"(理财), "all"(全部)
    """
    print("\n获取账户余额中...")
    
    if account_type == "all":
        # 显示所有账户
        all_balances = get_all_balances()
        
        # 现货账户
        print("\n" + "="*50)
        print("📊 现货账户 (Spot)")
        print("="*50)
        spot = all_balances.get("spot", {})
        if spot:
            for asset, balance in spot.items():
                print(f"  {asset}: {balance['free']:.8f} (可用) / {balance['locked']:.8f} (锁定)")
        else:
            print("  (空)")
        
        # 资金账户
        print("\n" + "="*50)
        print("💰 资金账户 (Funding) - 用于充提/C2C")
        print("="*50)
        funding = all_balances.get("funding", {})
        if funding:
            for asset, balance in funding.items():
                print(f"  {asset}: {balance['free']:.8f} (可用) / {balance['locked']:.8f} (锁定) / {balance['freeze']:.8f} (冻结)")
        else:
            print("  (空)")
        
        # 理财账户
        print("\n" + "="*50)
        print("📈 理财账户 (Earn)")
        print("="*50)
        earn = all_balances.get("earn", {})
        if earn:
            for asset, balance in earn.items():
                print(f"  {asset}: {balance['flexible']:.8f} (活期) / {balance['locked']:.8f} (定期)")
        else:
            print("  (空)")
        
        # 汇总
        print("\n" + "="*50)
        print("📋 资产汇总")
        print("="*50)
        summary = {}
        for asset, balance in spot.items():
            summary[asset] = summary.get(asset, 0) + balance['free'] + balance['locked']
        for asset, balance in funding.items():
            summary[asset] = summary.get(asset, 0) + balance['free'] + balance['locked'] + balance['freeze']
        for asset, balance in earn.items():
            summary[asset] = summary.get(asset, 0) + balance['flexible'] + balance['locked']
        
        if summary:
            for asset, total in sorted(summary.items(), key=lambda x: -x[1]):
                print(f"  {asset}: {total:.8f}")
        else:
            print("  无资产")
            
    elif account_type == "spot":
        balances = get_spot_balance()
        print("\n📊 现货账户余额:")
        print("-" * 40)
        if balances:
            for asset, balance in balances.items():
                print(f"  {asset}: {balance['free']:.8f} (可用) / {balance['locked']:.8f} (锁定)")
        else:
            print("  (空)")
            
    elif account_type == "funding":
        balances = get_funding_balance()
        print("\n💰 资金账户余额:")
        print("-" * 40)
        if balances:
            for asset, balance in balances.items():
                print(f"  {asset}: {balance['free']:.8f} (可用) / {balance['locked']:.8f} (锁定)")
        else:
            print("  (空)")
            
    elif account_type == "earn":
        balances = get_earn_balance()
        print("\n📈 理财账户余额:")
        print("-" * 40)
        if balances:
            for asset, balance in balances.items():
                print(f"  {asset}: {balance['flexible']:.8f} (活期) / {balance['locked']:.8f} (定期)")
        else:
            print("  (空)")


def show_networks(coin: str):
    """显示指定币种支持的网络"""
    print(f"\n获取 {coin} 的网络信息中...")
    info = get_coin_info(coin)
    
    if info:
        print(f"\n{coin} 支持的提现网络:")
        print("-" * 60)
        for network in info.get("networkList", []):
            status = "✓" if network.get("withdrawEnable") else "✗"
            print(f"  [{status}] {network['network']}")
            print(f"      名称: {network['name']}")
            print(f"      最小提现: {network.get('withdrawMin', 'N/A')}")
            print(f"      手续费: {network.get('withdrawFee', 'N/A')}")
            print()
    else:
        print(f"找不到 {coin} 的信息")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Binance 批量提现工具")
    parser.add_argument("--balance", "-b", action="store_true", help="显示账户余额")
    parser.add_argument("--account", "-a", type=str, default="all", 
                       choices=["all", "spot", "funding", "earn"],
                       help="账户类型: all(全部), spot(现货), funding(资金), earn(理财)")
    parser.add_argument("--networks", "-n", type=str, help="显示指定币种支持的网络")
    parser.add_argument("--withdraw", "-w", action="store_true", help="执行批量提现")
    parser.add_argument("--dry-run", "-d", action="store_true", help="模拟运行，不实际执行提现")
    parser.add_argument("--file", "-f", type=str, default=WITHDRAW_FILE, help="提现地址文件路径")
    parser.add_argument("--delay", type=float, default=1.0, help="每次提现之间的延迟（秒）")
    parser.add_argument("--history", "-H", action="store_true", help="显示提现历史")
    parser.add_argument("--test-proxy", "-t", action="store_true", help="测试代理连接")
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("Binance 批量提现工具")
    print("="*60)
    
    if args.test_proxy:
        test_proxy_connection()
        return
    
    if args.balance:
        show_balance(args.account)
    
    elif args.networks:
        show_networks(args.networks.upper())
    
    elif args.history:
        print("\n获取提现历史中...")
        history = get_withdraw_history(limit=20)
        if history:
            print("\n最近提现记录:")
            print("-" * 80)
            for h in history:
                print(f"  [{h.get('status')}] {h.get('coin')} {h.get('amount')}")
                print(f"    地址: {h.get('address')}")
                print(f"    网络: {h.get('network')}")
                print(f"    时间: {h.get('applyTime')}")
                print()
        else:
            print("暂无提现记录")
    
    elif args.withdraw:
        # 首先测试代理连接
        if PROXIES and not args.dry_run:
            if not test_proxy_connection():
                print("\n代理连接失败，无法继续提现操作")
                print("请检查代理配置是否正确")
                return
        
        # 加载提现地址
        addresses = load_withdraw_addresses(args.file)
        
        if not addresses:
            print("没有找到提现地址，请检查配置文件")
            return
        
        # 确认执行
        if not args.dry_run:
            print(f"\n即将执行 {len(addresses)} 个提现任务")
            print("请确认以下信息:")
            for addr in addresses:
                print(f"  - {addr['coin']} {addr['amount']} -> {addr['address'][:20]}...")
            
            confirm = input("\n确认执行提现? (输入 'yes' 确认): ")
            if confirm.lower() != "yes":
                print("已取消")
                return
        
        # 执行批量提现
        results = batch_withdraw(
            addresses=addresses,
            delay=args.delay,
            dry_run=args.dry_run
        )
        
        # 保存结果
        save_result(results)
    
    else:
        parser.print_help()
        print("\n示例:")
        print("  测试代理:       python batch_withdraw.py --test-proxy")
        print("  查看所有余额:   python batch_withdraw.py --balance")
        print("  查看现货余额:   python batch_withdraw.py --balance --account spot")
        print("  查看资金余额:   python batch_withdraw.py --balance --account funding")
        print("  查看理财余额:   python batch_withdraw.py --balance --account earn")
        print("  查看网络:       python batch_withdraw.py --networks USDT")
        print("  模拟提现:       python batch_withdraw.py --withdraw --dry-run")
        print("  执行提现:       python batch_withdraw.py --withdraw")
        print("  查看历史:       python batch_withdraw.py --history")


if __name__ == "__main__":
    main()

