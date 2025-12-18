import requests
import uuid
import random
import time
import imaplib
import email
import ssl
import re
import os
import csv  # 引入 csv 库
from email.header import decode_header
from typing import Optional, Dict, Any, List, Tuple

# ==================== 全局配置区域 ====================

# IMAP 邮箱配置 - 请通过环境变量或配置文件设置敏感信息
IMAP_FIXED_CONFIG = {
    "PASSWORD": os.getenv("IMAP_PASSWORD", "YOUR_IMAP_PASSWORD"),  # 设置环境变量或替换为你的密码
    "SERVER": os.getenv("IMAP_SERVER", "imap.example.com"),  # IMAP服务器地址
    "PORT": int(os.getenv("IMAP_PORT", "993")),
    "USE_SSL": True
}

# HTTP 基础配置 (保持不变)
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


# ==================== IMAP 邮件处理函数 ====================

def extract_verification_code(body_content: str) -> Optional[str]:
    pattern = re.compile(r'(?:code\s*is:[\s*]*|[\s*]*)(\d{6})')
    match = pattern.search(body_content)
    if match: return match.group(1)
    alt_pattern = re.compile(r'(?<!\d)\d{6}(?!\d)')
    alt_matches = alt_pattern.findall(body_content)
    if len(alt_matches) == 1: return alt_matches[0]
    return None


def decode_mail_header(header_value: Optional[str]) -> str:
    if not header_value: return ""
    decoded_parts = decode_header(header_value)
    decoded_string = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
            except:
                decoded_string += part.decode('utf-8', errors='ignore')
        else:
            decoded_string += part
    return decoded_string.strip()


def get_latest_email_content(
        server: str, port: int, user: str, password: str, use_ssl: bool = True
) -> Optional[Dict[str, Any]]:
    try:
        if use_ssl:
            context = ssl.create_default_context()
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            mail = imaplib.IMAP4_SSL(server, port, ssl_context=context)
        else:
            mail = imaplib.IMAP4(server, port)

        mail.login(user, password)
        mail.select('inbox', readonly=True)

        status, email_ids = mail.search(None, 'ALL')
        if status != 'OK': mail.logout(); return None

        list_of_ids = email_ids[0].split()
        if not list_of_ids: mail.logout(); return None

        latest_email_id = list_of_ids[-1]

        status, msg_data = mail.fetch(latest_email_id, '(RFC822)')
        if status != 'OK': mail.logout(); return None

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = decode_mail_header(msg['Subject'])
        sender = decode_mail_header(msg['From'])
        date = msg['Date']

        body_content = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = part.get('Content-Disposition')
                if ctype in ("text/plain", "text/html") and not cdispo:
                    try:
                        charset = part.get_content_charset()
                        body_content = part.get_payload(decode=True).decode(charset or 'utf-8', errors='ignore')
                    except Exception:
                        body_content = "[无法解析邮件正文]"
                    break
        else:
            try:
                charset = msg.get_content_charset()
                body_content = msg.get_payload(decode=True).decode(charset or 'utf-8', errors='ignore')
            except:
                body_content = "[无法解析邮件正文]"

        verification_code = extract_verification_code(body_content)

        mail.logout()

        return {
            "Subject": subject,
            "From": sender,
            "Date": date,
            "Body": body_content,
            "VerificationCode": verification_code
        }

    except imaplib.IMAP4.error as e:
        print(f"⚠️ IMAP 错误: {e}")
    except Exception as e:
        print(f"⚠️ 邮件获取异常: {e}")
    return None


# ==================== API 流程函数 ====================

def _generate_dynamic_headers(user_agent: str, include_content_type: bool = False) -> Dict[str, str]:
    """生成动态的 sentry 和 User-Agent 头部"""
    trace_id = str(uuid.uuid4()).replace('-', '')[:32]
    span_id = str(uuid.uuid4())[:16]

    headers = {
        'User-Agent': user_agent,
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'baggage': f'sentry-environment=prod,sentry-release=820441749c298c6720c76eb57d0c348f5b7027bd,sentry-public_key=90dba384c939a12a890c037474951990,sentry-trace_id={trace_id},sentry-sample_rate=0.1,sentry-sampled=false',
        'sentry-trace': f'{trace_id}-{span_id}-0',
        'Referer': 'https://app.fight.id/',
        'Origin': 'https://app.fight.id',
        'accept': '*/*'
    }

    if include_content_type: headers['content-type'] = 'application/json'
    return headers


def get_email_nonce(
        auth_bearer_token: str, step_name: str, max_retries: int = 3
) -> Optional[Dict[str, str]]:
    """调用 /auth/email/nonce 接口，获取 Nonce 和 ID。"""
    url = "https://api.fight.id/auth/email/nonce"
    user_agent = random.choice(user_agents)
    base_headers = {'Authorization': f'Bearer {auth_bearer_token}'}

    for attempt in range(max_retries):
        try:
            dynamic_headers = _generate_dynamic_headers(user_agent)
            headers = {**base_headers, **dynamic_headers}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json().get('data', {})
                return {'nonce': data.get('nonce'), 'id': data.get('id')}

            elif response.status_code == 401:
                return None

            if attempt < max_retries - 1:
                time.sleep(1)

        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue

    return None


def request_otp_email(
        auth_bearer_token: str, nonce: str, nonce_id: str, email_address: str, max_retries: int = 3
) -> bool:
    """调用 /auth/email/add/request 接口，请求发送验证码到指定邮箱。"""
    url = "https://api.fight.id/auth/email/add/request"
    user_agent = random.choice(user_agents)
    base_headers = {'Authorization': f'Bearer {auth_bearer_token}'}

    request_data = {"nonce": nonce, "nonceId": nonce_id, "email": email_address}

    for attempt in range(max_retries):
        try:
            dynamic_headers = _generate_dynamic_headers(user_agent, include_content_type=True)
            headers = {**base_headers, **dynamic_headers}

            response = requests.post(url, headers=headers, json=request_data, timeout=10)

            if response.status_code == 201:
                result = response.json()
                if result.get('success') is True:
                    return True
                else:
                    return False

            elif response.status_code == 400:
                return False

            if attempt < max_retries - 1:
                time.sleep(1)

        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue

    return False


def verify_otp_email(
        auth_bearer_token: str, nonce: str, nonce_id: str, email_address: str, otp_code: str, max_retries: int = 3
) -> bool:
    """Step B2: 调用 /auth/email/add/verify 接口，使用 OTP 验证邮箱。"""
    url = "https://api.fight.id/auth/email/add/verify"
    user_agent = random.choice(user_agents)
    base_headers = {'Authorization': f'Bearer {auth_bearer_token}'}

    request_data = {"nonce": nonce, "nonceId": nonce_id, "email": email_address, "otp": otp_code}

    for attempt in range(max_retries):
        try:
            dynamic_headers = _generate_dynamic_headers(user_agent, include_content_type=True)
            headers = {**base_headers, **dynamic_headers}

            response = requests.post(url, headers=headers, json=request_data, timeout=10)

            if response.status_code == 201:
                result = response.json()
                if result.get('success') is True:
                    return True
                else:
                    return False

            elif response.status_code == 400:
                return False

            if attempt < max_retries - 1:
                time.sleep(1)

        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue

    return False


# ==================== 统一流程函数 ====================

def main_verification_flow(token: str, imap_config: Dict[str, Any]) -> bool:
    """
    执行获取 Nonce -> 请求发送验证码 -> 检查邮箱 -> 验证验证码的完整流程。
    返回绑定是否成功 (True/False)。
    """
    email_address = imap_config["ADDRESS"]

    if not token or len(token.strip()) < 50:
        print("🛑 严重错误：Bearer Token 配置无效或缺失！")
        return False

    print(f"🚀 开始邮箱验证流程 (邮箱: {email_address})")

    # --- 阶段 A: 请求并获取验证码 ---
    nonce_data_req = get_email_nonce(token, step_name="Step A1")
    if not nonce_data_req:
        print("❌ Step A1: 获取请求 Nonce 失败或 Token 无效。")
        return False
    nonce_req = nonce_data_req.get('nonce')
    nonce_id_req = nonce_data_req.get('id')

    if not request_otp_email(token, nonce_req, nonce_id_req, email_address):
        print("❌ Step A2: 请求发送验证码失败。")
        return False

    random_wait_time = random.randint(3, 8)
    CHECK_INTERVAL = 5
    MAX_CHECKS = 6

    print(f"⏳ Step A3: 等待邮件 (随机等待 {random_wait_time}秒)...")
    time.sleep(random_wait_time)

    verification_code = None
    for i in range(1, MAX_CHECKS + 1):
        email_data = get_latest_email_content(
            imap_config["SERVER"], imap_config["PORT"], imap_config["ADDRESS"],
            imap_config["PASSWORD"], imap_config["USE_SSL"]
        )

        if email_data and email_data.get("VerificationCode"):
            verification_code = email_data["VerificationCode"]
            print(f"🎉 成功提取到验证码: {verification_code}")
            break

        if i < MAX_CHECKS:
            time.sleep(CHECK_INTERVAL)

    if not verification_code:
        print("❌ Step A3: 未能成功提取验证码。")
        return False

    # --- 阶段 B: 验证验证码 ---
    nonce_data_verify = get_email_nonce(token, step_name="Step B1")
    if not nonce_data_verify:
        print("❌ Step B1: 获取验证 Nonce 失败或 Token 无效。")
        return False

    nonce_verify = nonce_data_verify.get('nonce')
    nonce_id_verify = nonce_data_verify.get('id')

    success = verify_otp_email(
        token, nonce_verify, nonce_id_verify, email_address, verification_code
    )

    if success:
        print("✅ 邮箱验证/绑定成功。")
    else:
        print("❌ 邮箱验证/绑定失败。")

    return success


# ==================== 主程序执行 ====================

def run_csv_flow(csv_filename: str = "tokens_email_info.csv"):
    """
    按行读取 CSV 文件，执行绑定流程，并输出报告。
    """
    print("=" * 60)
    print(f"🧾 正在从文件 {csv_filename} 读取数据并开始批量绑定...")
    print("=" * 60)

    results: List[Tuple[str, str, str]] = []

    try:
        with open(csv_filename, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            if not all(col in reader.fieldnames for col in ["wallet", "token", "email"]):
                print("🛑 错误: CSV 文件缺少 'wallet', 'token' 或 'email' 列。")
                return

            for row in reader:
                wallet = row.get("wallet", "").strip()
                token = row.get("token", "").strip()
                email_address = row.get("email", "").strip()

                print("\n" + "#" * 30 + f" 开始处理 {wallet} " + "#" * 30)

                if not token:
                    status = "跳过 (Token 为空)"
                    print(f"⚠️ {wallet} - {email_address}: {status}")
                    results.append((wallet, email_address, status))
                    continue

                if not email_address:
                    status = "跳过 (Email 为空)"
                    print(f"⚠️ {wallet} - Token 存在: {status}")
                    results.append((wallet, "N/A", status))
                    continue

                current_imap_config = IMAP_FIXED_CONFIG.copy()
                current_imap_config["ADDRESS"] = email_address
                current_imap_config["USER"] = email_address

                try:
                    success = main_verification_flow(token, current_imap_config)
                    status = "绑定成功" if success else "绑定失败 (Token/OTP问题)"
                except Exception as e:
                    status = f"程序异常 ({type(e).__name__})"
                    print(f"致命异常: {e}")

                results.append((wallet, email_address, status))
                print(f"结果: {wallet} -> {status}")
                print("#" * 65)
                time.sleep(random.uniform(5, 10))

    except FileNotFoundError:
        print(f"❌ 错误: 文件 {csv_filename} 未找到。请确保文件存在于脚本的同级目录。")
        return

    except Exception as e:
        print(f"❌ 读取或处理 CSV 文件时发生未知错误: {e}")
        return

    # 输出报告
    print("\n" + "=" * 60)
    print("📊 批量绑定报告")
    print("=" * 60)
    print(f"{'Wallet':<40} {'Status':<30}")
    print("-" * 70)
    for wallet, email_addr, status in results:
        print(f"{wallet:<40} {status:<30}")
    print("=" * 60)


if __name__ == "__main__":
    run_csv_flow()

