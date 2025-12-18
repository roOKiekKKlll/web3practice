# Fight.ID Claim Point Script
# 批量领取 Streak Rewards

import requests
import csv
import os
import random
import time

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


def claim_streak_rewards():
    input_csv = "tokens.csv"
    output_csv = "claim.csv"

    if not os.path.exists(input_csv):
        print(f"❌ 文件 {input_csv} 不存在，请确保 tokens.csv 在当前目录")
        return

    headers = {
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

    results = []

    try:
        with open(input_csv, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            total_rows = 0
            valid_rows = 0

            for row in reader:
                total_rows += 1
                wallet = row.get('wallet', '').strip()
                token = row.get('token', '').strip()

                if not wallet or not token:
                    print(f"⚠️  跳过第 {total_rows} 行：wallet 或 token 为空")
                    continue

                valid_rows += 1
                print(f"\n🔁 正在处理钱包: {wallet[:12]}... (第 {valid_rows}/{total_rows} 个有效行)")

                headers['authorization'] = f'Bearer {token}'

                try:
                    response = requests.post(
                        'https://api.fight.id/streaks/rewards/claim',
                        headers=headers,
                        json={},
                        timeout=15
                    )

                    status_code = response.status_code
                    print(f"   📥 状态码: {status_code}")

                    if status_code == 201:
                        try:
                            json_data = response.json()
                            success = json_data.get('success', False)
                            if success:
                                message = json_data.get('data', {}).get('message', '')
                                print(f"   ✅ 领取成功: {message}")
                                results.append({'wallet': wallet, 'result': '领取成功'})
                            else:
                                print(f"   ❌ 接口返回 success=False")
                                results.append({'wallet': wallet, 'result': '领取失败（success=False）'})
                        except Exception as e:
                            print(f"   ⚠️  解析返回JSON出错: {e}")
                            results.append({'wallet': wallet, 'result': '领取失败（解析异常）'})
                    else:
                        print(f"   ❌ 状态码不是 201，实际为 {status_code}")
                        try:
                            err_text = response.text[:200]
                            print(f"   🔍 错误信息: {err_text}")
                        except:
                            pass
                        results.append({'wallet': wallet, 'result': f'领取失败（状态码 {status_code}）'})

                except requests.exceptions.RequestException as e:
                    print(f"   ❌ 网络请求异常: {e}")
                    results.append({'wallet': wallet, 'result': f'领取失败（网络异常）'})

                print("   ⏳ 等待 1 秒后继续...")
                time.sleep(1)

    except Exception as e:
        print(f"❌ 读取或处理文件时发生异常: {e}")
        return

    try:
        with open(output_csv, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['wallet', 'result']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for item in results:
                writer.writerow(item)
        print(f"\n✅ 领取结果已保存至: {output_csv}")
        print(f"📊 总计处理 {valid_rows} 个有效钱包，结果已记录")
    except Exception as e:
        print(f"❌ 保存结果文件失败: {e}")


if __name__ == '__main__':
    print("🎯 开始调用 FightID Streak Rewards Claim 接口")
    claim_streak_rewards()

