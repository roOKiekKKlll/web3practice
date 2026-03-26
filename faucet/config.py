"""
Google Cloud Web3 Hoodi Faucet - 配置管理
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


# reCAPTCHA Enterprise 配置
RECAPTCHA_SITE_KEY = "6Lc_AHopAAAAAKocwvk6MQcAFV2xjwcQdqlBRHj5"
RECAPTCHA_PAGE_URL = "https://cloud.google.com/application/web3/faucet/ethereum/hoodi"

# Faucet API 配置
FAUCET_BASE_URL = "https://cloud.google.com/application/web3/_/Web3Portal/data/batchexecute"
FAUCET_RPC_ID = "Yf4tfc"
FAUCET_NETWORK = "ethereum/hoodi"
FAUCET_SOURCE_PATH = "/application/web3/faucet/ethereum/hoodi"

# 请求头模板
DEFAULT_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
    "origin": "https://cloud.google.com",
    "referer": "https://cloud.google.com/",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "x-same-domain": "1",
}


@dataclass
class FaucetConfig:
    """Faucet 自动化配置"""

    # 验证码服务
    captcha_service: str = os.getenv("CAPTCHA_SERVICE", "2captcha")
    twocaptcha_api_key: str = os.getenv("TWOCAPTCHA_API_KEY", "")
    capsolver_api_key: str = os.getenv("CAPSOLVER_API_KEY", "")

    # 钱包地址
    wallet_addresses: List[str] = field(default_factory=list)

    # Google Cookie（完整字符串）
    google_cookies: str = os.getenv("GOOGLE_COOKIES", "")

    # 会话参数（从页面动态提取）
    at_token: str = ""  # XSRF token
    bl_token: str = ""  # Build label
    f_sid: str = ""     # Session ID

    def __post_init__(self):
        if not self.wallet_addresses:
            addrs = os.getenv("WALLET_ADDRESSES", "")
            if addrs:
                self.wallet_addresses = [a.strip() for a in addrs.split(",") if a.strip()]

    @property
    def captcha_api_key(self) -> str:
        if self.captcha_service == "2captcha":
            return self.twocaptcha_api_key
        elif self.captcha_service == "capsolver":
            return self.capsolver_api_key
        return ""

    def validate(self) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        if not self.captcha_api_key:
            errors.append(f"缺少 {self.captcha_service} API Key")
        if not self.wallet_addresses:
            errors.append("缺少钱包地址")
        if not self.google_cookies:
            errors.append("缺少 Google Cookie")
        return errors
