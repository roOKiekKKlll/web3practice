# Fight.ID Bind Aptos Wallet Script
# 批量绑定 Aptos 钱包

import requests
import time
import csv
from aptos_sdk.account import Account


def get_apt_address_and_sign(private_key_hex: str, message: str):
    """从十六进制私钥获取 Aptos 地址和签名"""
    try:
        if private_key_hex.startswith('0x') or private_key_hex.startswith('0X'):
            private_key_hex = private_key_hex[2:]

        account = Account.load_key("0x" + private_key_hex)
        address = str(account.address())

        if isinstance(message, bytes):
            message_bytes = message
        else:
            message_bytes = message.encode('utf-8')

        signature = account.private_key.sign(message_bytes)
        signature_hex = signature.data().hex()

        return address, signature_hex
    except Exception as e:
        import traceback
        raise Exception(f"Failed to process Aptos wallet: {str(e)}\n{traceback.format_exc()}")


def get_nonce(bearer_token: str):
    """获取 nonce 信息"""
    url = 'https://api.fight.id/user/link-siwa/nonce'
    headers = {
        'accept': '*/*',
        'accept-language': 'zh-TW,zh;q=0.9',
        'authorization': f'Bearer {bearer_token}',
        'baggage': 'sentry-environment=prod,sentry-release=820441749c298c6720c76eb57d0c348f5b7027bd,sentry-public_key=90dba384c939a12a890c037474951990,sentry-trace_id=fe0569b208904250a0acf509187ed218,sentry-sample_rate=0.1,sentry-sampled=true',
        'cache-control': 'no-cache',
        'origin': 'https://app.fight.id',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sentry-trace': 'fe0569b208904250a0acf509187ed218-8c2c583f9e836a27-1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    }

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise Exception(f"Nonce request failed: {resp.status_code} {resp.text}")

    data = resp.json()['data']
    return data


def bind_aptos_wallet(bearer_token: str, apt_private_key: str, verbose=False):
    """
    绑定 Aptos 钱包
    返回: (success: bool, apt_address: str, message: str)
    """
    try:
        nonce_data = get_nonce(bearer_token)
        if verbose:
            print(f"✅ Got nonce: {nonce_data['nonce']}")

        statement = "Link your wallet or secondary email to your account."
        full_message = f"APTOS\nmessage: {statement}\nnonce: {nonce_data['nonce']}"

        apt_address, signature = get_apt_address_and_sign(apt_private_key, full_message)
        if verbose:
            print(f"📍 Aptos Address: {apt_address}")

        url = 'https://api.fight.id/user/link-siwa/callback'

        input_data = {
            "nonce": nonce_data['nonce'],
            "nonceId": nonce_data['nonceId'],
            "resources": nonce_data['resources'],
            "statement": nonce_data['statement']
        }

        timestamp_ms = int(time.time() * 1000)
        output_data = {
            "address": apt_address,
            "signature": signature,
            "nonce": nonce_data['nonce'],
            "message": statement,
            "fullMessage": full_message,
            "domain": "app.fight.id",
            "statement": statement,
            "email": "",
            "timestamp": timestamp_ms,
            "chain": "aptos"
        }

        payload = {
            "input": input_data,
            "output": output_data
        }

        headers = {
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'sec-ch-ua-mobile': '?0',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'authorization': f'Bearer {bearer_token}',
            'content-type': 'application/json',
            'origin': 'https://app.fight.id',
            'Referer': '',
            'baggage': 'sentry-environment=prod,sentry-release=820441749c298c6720c76eb57d0c348f5b7027bd,sentry-public_key=90dba384c939a12a890c037474951990,sentry-trace_id=818583fff42f4792b47ae0d33ee97078,sentry-sample_rate=0.1,sentry-sampled=false',
            'sentry-trace': '818583fff42f4792b47ae0d33ee97078-b7f29341bb5f823b-0',
            'sec-ch-ua-platform': '"Windows"'
        }

        resp = requests.post(url, json=payload, headers=headers)

        if verbose:
            print(f"📡 Status Code: {resp.status_code}")
            print(f"📦 Response: {resp.text}")

        if resp.status_code == 201:
            json_resp = resp.json()
            if json_resp.get("success"):
                return True, apt_address, "绑定成功"
            else:
                return False, apt_address, f"绑定失败: {json_resp}"
        else:
            return False, apt_address, f"HTTP {resp.status_code}: {resp.text}"

    except Exception as e:
        apt_addr = "未知"
        try:
            apt_addr, _ = get_apt_address_and_sign(apt_private_key, "test")
        except:
            pass
        return False, apt_addr, f"错误: {str(e)}"


def batch_bind_wallets():
    """批量绑定钱包"""
    print("=" * 60)
    print("🚀 开始批量绑定 Aptos 钱包")
    print("=" * 60)

    try:
        with open('tokens.csv', 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            tokens_data = list(csv_reader)
    except FileNotFoundError:
        print("❌ 错误: tokens.csv 文件不存在")
        return
    except Exception as e:
        print(f"❌ 读取 tokens.csv 失败: {str(e)}")
        return

    try:
        with open('apt_wallet.txt', 'r', encoding='utf-8') as f:
            apt_wallets = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ 错误: apt_wallet.txt 文件不存在")
        return
    except Exception as e:
        print(f"❌ 读取 apt_wallet.txt 失败: {str(e)}")
        return

    if len(tokens_data) != len(apt_wallets):
        print(f"⚠️  警告: tokens.csv 有 {len(tokens_data)} 行数据，apt_wallet.txt 有 {len(apt_wallets)} 行")
        print(f"⚠️  将处理前 {min(len(tokens_data), len(apt_wallets))} 个钱包")

    results = []
    total = min(len(tokens_data), len(apt_wallets))
    success_count = 0
    skip_count = 0
    fail_count = 0

    print(f"\n📊 总计需要处理: {total} 个钱包")
    print("-" * 60)

    for i, (token_row, apt_private_key) in enumerate(zip(tokens_data, apt_wallets), 1):
        bsc_wallet = token_row.get('wallet', '').strip()
        bearer_token = token_row.get('token', '').strip()

        print(f"\n[{i}/{total}] 处理 BSC 地址: {bsc_wallet}")

        if not bearer_token:
            print(f"⏭️  跳过: Token 为空")
            skip_count += 1
            results.append({
                'bsc': bsc_wallet,
                'apt': '',
                'result': '跳过(Token为空)'
            })
            continue

        if not apt_private_key:
            print(f"⏭️  跳过: Aptos 私钥为空")
            skip_count += 1
            results.append({
                'bsc': bsc_wallet,
                'apt': '',
                'result': '跳过(私钥为空)'
            })
            continue

        try:
            success, apt_address, message = bind_aptos_wallet(bearer_token, apt_private_key, verbose=True)

            if success:
                print(f"✅ 成功: {message}")
                success_count += 1
                results.append({
                    'bsc': bsc_wallet,
                    'apt': apt_address,
                    'result': '绑定成功'
                })
            else:
                print(f"❌ 失败: {message}")
                fail_count += 1
                results.append({
                    'bsc': bsc_wallet,
                    'apt': apt_address,
                    'result': f'绑定失败: {message}'
                })
        except Exception as e:
            print(f"💥 异常: {str(e)}")
            fail_count += 1
            results.append({
                'bsc': bsc_wallet,
                'apt': '',
                'result': f'异常: {str(e)}'
            })

        if i < total:
            time.sleep(1)

    print("\n" + "=" * 60)
    print("💾 保存结果到 apt_bsc.csv")
    try:
        with open('apt_bsc.csv', 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['bsc', 'apt', 'result'])
            writer.writeheader()
            writer.writerows(results)
        print("✅ 结果已保存")
    except Exception as e:
        print(f"❌ 保存结果失败: {str(e)}")

    print("\n" + "=" * 60)
    print("📊 批量绑定完成！统计结果:")
    print(f"   总计: {total} 个")
    print(f"   ✅ 成功: {success_count} 个")
    print(f"   ❌ 失败: {fail_count} 个")
    print(f"   ⏭️  跳过: {skip_count} 个")
    print("=" * 60)


if __name__ == "__main__":
    batch_bind_wallets()

