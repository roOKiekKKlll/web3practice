# Fight.ID Fetch Referral Code Script
# 批量获取 Referral Code

import requests
import csv
import os
import random

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


def fetch_referral_codes():
    input_csv = "tokens.csv"
    output_csv = "referral_info_main.csv"

    if not os.path.exists(input_csv):
        print(f"❌ 输入文件 {input_csv} 不存在！")
        return

    wallets = []
    tokens = []
    valid_rows = []

    try:
        with open(input_csv, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                wallet = row.get('wallet', '').strip()
                token = row.get('token', '').strip()
                if wallet and token:
                    wallets.append(wallet)
                    tokens.append(token)
                    valid_rows.append(True)
                else:
                    wallets.append(wallet if wallet else f"EMPTY_WALLET_{len(wallets)}")
                    tokens.append("")
                    valid_rows.append(False)
    except Exception as e:
        print(f"❌ 读取 {input_csv} 失败: {e}")
        return

    total = len(wallets)
    print(f"📋 共读取 {total} 行数据，其中 {sum(valid_rows)} 行 wallet 和 token 均有效")

    referral_codes = []

    headers_template = {
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': random.choice(user_agents),
        'Referer': '',
        'sec-ch-ua-platform': '"Windows"',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'Origin': 'https://app.fight.id',
    }

    for i, (wallet, token) in enumerate(zip(wallets, tokens)):
        print(f"\n🔍 正在处理第 {i+1}/{total} 个钱包: {wallet[:12]}...")
        referral_code = ""

        if not token:
            print("   ⚠️  Token为空，跳过请求")
        else:
            headers = headers_template.copy()
            headers['authorization'] = f'Bearer {token}'

            try:
                response = requests.get(
                    'https://api.fight.id/referrals/info',
                    headers=headers,
                    json={},
                    timeout=15
                )
                status_code = response.status_code
                print(f"   📥 状态码: {status_code}")

                if status_code == 200:
                    try:
                        json_data = response.json()
                        success = json_data.get('success', False)
                        if success:
                            data = json_data.get('data', {})
                            referral_code = data.get('referralCode', '')
                            if referral_code:
                                print(f"   ✅ 获取成功，referralCode: {referral_code}")
                            else:
                                print("   ⚠️  接口返回 success=true，但 referralCode 为空")
                        else:
                            print("   ❌ 接口返回 success=false")
                    except Exception as e:
                        print(f"   ⚠️  解析 JSON 失败: {e}")
                else:
                    print(f"   ❌ 状态码非 200，实际为 {status_code}")
                    try:
                        err_text = response.text[:200]
                        print(f"   🔍 错误信息: {err_text}")
                    except:
                        pass

            except requests.exceptions.RequestException as e:
                print(f"   ❌ 网络请求异常: {e}")

        referral_codes.append(referral_code)

    try:
        with open(output_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['wallet', 'referralCode'])

            for wallet, code in zip(wallets, referral_codes):
                writer.writerow([wallet, code])

        print(f"\n✅ 结果已写入: {output_csv}")
        print(f"📊 总计处理 {total} 个钱包")
        success_count = sum(1 for code in referral_codes if code)
        print(f"   ➕ 成功获取 referralCode 的钱包: {success_count} 个")
        print(f"   ➖ 未获取到 referralCode 的钱包: {total - success_count} 个")

    except Exception as e:
        print(f"❌ 写入 {output_csv} 失败: {e}")


if __name__ == '__main__':
    print("🎯 开始批量获取 Referral Code 信息")
    fetch_referral_codes()

