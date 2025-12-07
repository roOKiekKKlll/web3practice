import requests
from typing import Dict, Optional, Any, Callable
from urllib.parse import urlparse, parse_qs
import time
import json
import hmac
import hashlib
import base64


class DiscordAuth:
    """Discord OAuth2 认证工具类，用于获取授权码 (auth_code)"""

    # --- 常量定义 (保持不变) ---
    DISCORD_API_BASE = "https://discord.com/api/v10"
    DISCORD_AUTHORIZE_URL = f"{DISCORD_API_BASE}/oauth2/authorize"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    MAX_RETRIES = 3
    RETRY_INTERVAL = 5

    def __init__(self, auth_token: str):
        if not auth_token:
            raise ValueError("auth_token不能为空 (用于模拟用户会话)")

        self.auth_token = auth_token
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """创建配置好的 requests session，增强模拟真实性。"""
        session = requests.Session()
        headers = {
            "user-agent": self.USER_AGENT,
            "authorization": self.auth_token,
            "Content-Type": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://discord.com/channels/@me",
            "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwidmhlYXJlIjoiOTYiLCJvcF9kZXZpY2VfaWQiOiJmNjEyNTBlNi03NGE1LTRkYjgtOTc1Yi0xM2RiM2E0MjRiZTIifQ==",
            "Origin": "https://discord.com"
        }
        session.headers.update(headers)
        return session

    def _handle_response(self, response: requests.Response, retry_func: Optional[Callable] = None) -> Optional[Any]:
        """处理响应状态和速率限制。"""
        if response.status_code == 429:
            print(f"⚠️ 遇到 429 速率限制。等待 {self.RETRY_INTERVAL} 秒后重试...")
            time.sleep(self.RETRY_INTERVAL)
            if retry_func:
                return retry_func()
            response.raise_for_status()

        if response.status_code >= 400 and response.status_code != 302 and response.status_code != 200:
            # 对于 200 状态码，允许通过，因为可能是 JSON 成功响应
            response.raise_for_status()

        return None

    def get_auth_code(self, client_id: str, redirect_uri: str, scope: str, state: Optional[str] = None,
                      prompt: Optional[str] = "consent") -> str:
        """
        执行 Discord OAuth2 流程：发送 GET 获取授权状态，然后 POST 批准授权。
        """

        params = {
            "client_id": client_id,
            "response_type": "code",
            "scope": scope,
            "redirect_uri": redirect_uri,
            "state": state or ""
        }
        if prompt:
            params['prompt'] = prompt

        # --- 步骤 1: GET 请求获取授权状态 (预期 JSON 响应) ---
        response = self.session.get(self.DISCORD_AUTHORIZE_URL, params=params)
        self._handle_response(response, lambda: self.get_auth_code(client_id, redirect_uri, scope, state))

        try:
            get_data = response.json()
        except json.JSONDecodeError:
            raise ValueError("GET 授权请求响应不是有效的 JSON 格式。")

        # --- 步骤 2: 执行 POST 批准授权 ---
        if get_data.get("authorized") is True:
            # 如果已经授权，Discord 应该直接重定向。如果返回 JSON，我们假设需要 POST
            pass

        if get_data.get("authorized") is False:
            post_data = {
                "permissions": "0",
                "authorize": "true",
            }

            # 再次 POST 到授权 URL，这次捕获 200 状态码中的 JSON
            response = self.session.post(
                self.DISCORD_AUTHORIZE_URL,
                params=params,
                json=post_data,
                allow_redirects=False
            )

            self._handle_response(response, lambda: self.get_auth_code(client_id, redirect_uri, scope, state))

            # 🚨 关键修改 1: 检查状态码是否为 200 (JSON 成功) 或 302 (Header 重定向)
            if response.status_code not in [200, 302]:
                print(f"🚨 授权失败，最终状态码: {response.status_code}")
                try:
                    print(f"错误详情: {response.json()}")
                except:
                    pass
                raise ValueError(f"授权 POST 请求失败，未收到成功状态码 ({response.status_code})。")

        # --- 步骤 3: 从响应中提取授权码 (Code) ---

        # 🚨 关键修改 2: 优先从 JSON 响应体中提取 location (适用于 200 状态码)
        redirect_url = None

        if response.status_code == 200:
            try:
                post_data_json = response.json()
                redirect_url = post_data_json.get("location")
                print("redirect_url：", redirect_url)
            except json.JSONDecodeError:
                pass  # 如果不是 JSON，尝试 Header

        # 如果 JSON 中没有 location，则尝试从 Header 中提取 (适用于 302 状态码)
        if not redirect_url and response.status_code == 302:
            redirect_url = response.headers.get("Location")

        if not redirect_url or "code=" not in redirect_url:
            raise ValueError("未在响应中找到有效的重定向 URL 或 'code' 参数。")

        # 解析 URL 中的 code
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        auth_code = query_params.get("code", [None])[0]

        if not auth_code:
            raise ValueError("解析重定向 URL 成功，但未找到有效的授权码。")

        return auth_code


def generate_signed_state(email: str, secret_key: bytes) -> str:
    """
    使用 HMAC-SHA256 (HS256) 算法生成 Discord OAuth2 的 state 参数。

    Args:
        email (str): 用户的邮箱地址 (作为 uid)。
        secret_key (bytes): 用于 HMAC 签名的秘密密钥 (必须是字节串)。

    Returns:
        str: 格式为 'Payload.Signature' 的 Base64 URL Safe 编码字符串。
    """

    # 1. 构建 Payload
    current_ms_ts = int(time.time() * 1000)
    payload: Dict[str, str | int] = {
        "uid": email,
        "ts": current_ms_ts
    }

    # 将 JSON 转换为紧凑、确定的字节串
    # separators=(',', ':') 确保没有空格，维持格式一致性
    json_bytes = json.dumps(
        payload,
        separators=(',', ':')
    ).encode('utf-8')

    # 2. Base64 URL Safe 编码 Payload
    encoded_payload = base64.urlsafe_b64encode(json_bytes).rstrip(b'=')

    # 3. HMAC-SHA256 签名
    h = hmac.new(secret_key, encoded_payload, hashlib.sha256)
    signature = h.digest()

    # 4. Base64 URL Safe 编码签名
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b'=')

    # 5. 拼接 Payload.Signature
    state_string = (encoded_payload.decode('utf-8') +
                    "." +
                    encoded_signature.decode('utf-8'))

    return state_string




# --- 示例用法 (请替换为您自己的值) ---
if __name__ == "__main__":
    MY_USER_AUTH_TOKEN = "your auth token"

    MY_CLIENT_ID = "1418246773956411514"
    MY_REDIRECT_URI = "https://api.fight.id/discord/verify/callback"
    MY_SCOPE = "identify guilds.members.read"
    # 请确保这个 STATE 是用您的密钥正确生成的

    MY_SECRET_KEY_B64_STRING = "Q9r_NlF1cRj8W9z4m-Xb_7kFv2sPzGj4E5yA8tC3aF0="
    MY_SECRET_KEY_BYTES = base64.urlsafe_b64decode(MY_SECRET_KEY_B64_STRING)
    EMAIL = "your email"  #这是分析实际验证时得state参数，可能不需要
    MY_STATE = generate_signed_state(EMAIL, MY_SECRET_KEY_BYTES)

    try:
        discord_auth = DiscordAuth(auth_token=MY_USER_AUTH_TOKEN)

        code = discord_auth.get_auth_code(
            client_id=MY_CLIENT_ID,
            redirect_uri=MY_REDIRECT_URI,
            scope=MY_SCOPE,
            state=MY_STATE
        )

        print("\n" + "=" * 50)
        print(f"🎉 成功获取 Discord 授权码 (auth_code):")
        print(f"CODE: {code}")
        print("=" * 50)

    except ValueError as e:
        print(f"\n❌ OAuth 流程失败: {e}")
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP 请求错误: {e}")
    except Exception as e:
        print(f"\n❌ 发生未知错误: {e}")