"""
Google Cloud Web3 Hoodi ETH Faucet 自动领水脚本

用法:
    python claim_faucet.py --wallet 0xYourAddress --cookies "cookie_string"
    python claim_faucet.py --wallet 0xAddr1,0xAddr2 --cookies-file cookies.txt
    python claim_faucet.py --dry-run  # 只打印请求，不实际发送
"""
import re
import json
import time
import random
import logging
import argparse
import urllib.parse
from typing import Optional, Tuple, List, Dict
import requests

from config import (
    FaucetConfig,
    RECAPTCHA_SITE_KEY,
    RECAPTCHA_PAGE_URL,
    FAUCET_BASE_URL,
    FAUCET_RPC_ID,
    FAUCET_NETWORK,
    FAUCET_SOURCE_PATH,
    DEFAULT_HEADERS,
)
from recaptcha_solver import RecaptchaSolver, RecaptchaSolverError

# ============================================================
#  日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================
#  Google batchexecute 协议相关
# ============================================================

class FaucetError(Exception):
    """Faucet 请求错误"""
    pass


class RateLimitError(FaucetError):
    """频率限制错误"""
    pass


class FaucetClaimer:
    """Google Cloud Web3 Faucet 领水器"""

    def __init__(self, config: FaucetConfig):
        self.config = config
        self.session = requests.Session()
        self._setup_session()
        self.solver = RecaptchaSolver(
            service=config.captcha_service,
            api_key=config.captcha_api_key,
        )

    def _setup_session(self):
        """初始化 HTTP 会话"""
        self.session.headers.update(DEFAULT_HEADERS)

        # 设置 cookies
        if self.config.google_cookies:
            cookie_dict = self._parse_cookies(self.config.google_cookies)
            for name, value in cookie_dict.items():
                self.session.cookies.set(name, value, domain=".google.com")

    @staticmethod
    def _parse_cookies(cookie_string: str) -> Dict[str, str]:
        """解析 cookie 字符串为字典"""
        cookies = {}
        for item in cookie_string.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                cookies[key.strip()] = value.strip()
        return cookies

    def _fetch_page_tokens(self) -> Tuple[str, str, str]:
        """
        从 faucet 页面提取动态 token：at (XSRF), bl (build label), f.sid

        Returns:
            (at_token, bl_token, f_sid)
        """
        logger.info("正在获取页面 token...")
        resp = self.session.get(RECAPTCHA_PAGE_URL, timeout=30)
        resp.raise_for_status()
        html = resp.text

        # 提取 at token (XSRF)
        at_match = re.search(r'"SNlM0e":"([^"]+)"', html)
        if not at_match:
            # 备用模式
            at_match = re.search(r'WIZ_global_data.*?"SNlM0e"\s*:\s*"([^"]+)"', html, re.DOTALL)
        if not at_match:
            raise FaucetError("无法从页面提取 XSRF token (at)。Cookie 可能已过期，请重新获取。")
        at_token = at_match.group(1)

        # 提取 bl token (build label)
        bl_match = re.search(r'"cfb2h":"([^"]+)"', html)
        if not bl_match:
            bl_match = re.search(r'"([^"]*boq_cloud-web3-portal[^"]*)"', html)
        bl_token = bl_match.group(1) if bl_match else "boq_cloud-web3-portal-web-ui_20260323.08_p0"

        # 提取 f.sid
        sid_match = re.search(r'"FdrFJe":"([^"]+)"', html)
        f_sid = sid_match.group(1) if sid_match else str(random.randint(10**18, 10**19 - 1))

        logger.info(f"  at token: {at_token[:20]}...")
        logger.info(f"  bl token: {bl_token}")
        logger.info(f"  f.sid:    {f_sid[:10]}...")

        return at_token, bl_token, f_sid

    def _build_request_body(
        self,
        wallet_addresses: List[str],
        recaptcha_token: str,
        at_token: str,
    ) -> str:
        """
        构造 batchexecute 请求体

        请求体结构 (URL decoded):
            f.req=[["Yf4tfc","[\"ethereum/hoodi\",[\"0xAddress\"],\"recaptcha_token\"]",null,"generic"]]
            &at=XSRF_TOKEN

        Args:
            wallet_addresses: 钱包地址列表
            recaptcha_token: reCAPTCHA Enterprise token
            at_token: XSRF token

        Returns:
            URL-encoded 的请求体字符串
        """
        # 内层 JSON: ["ethereum/hoodi",["0xAddr"],"recaptcha_token"]
        inner_json = json.dumps([
            FAUCET_NETWORK,
            wallet_addresses,
            recaptcha_token,
        ], separators=(',', ':'))

        # 外层 JSON 必须是三层嵌套: [[["Yf4tfc","<inner_json>",null,"generic"]]]
        outer = json.dumps([
            [[FAUCET_RPC_ID, inner_json, None, "generic"]]
        ], separators=(',', ':'))

        # URL-encode 整个请求体
        body = urllib.parse.urlencode({
            "f.req": outer,
            "at": at_token,
        })

        return body

    def _build_request_url(self, bl_token: str, f_sid: str, reqid: int) -> str:
        """构造 batchexecute 请求 URL"""
        params = {
            "rpcids": FAUCET_RPC_ID,
            "source-path": FAUCET_SOURCE_PATH,
            "bl": bl_token,
            "f.sid": f_sid,
            "hl": "en",
            "_reqid": str(reqid),
            "rt": "c",
        }
        return f"{FAUCET_BASE_URL}?{urllib.parse.urlencode(params)}"

    @staticmethod
    def _parse_response(raw_response: str) -> dict:
        """
        解析 Google batchexecute 响应

        响应格式:
            )]}'
            <length>
            [["wrb.fr","Yf4tfc","<result>",null,null,null,"generic"],...]

        Returns:
            解析后的结果字典
        """
        # 去掉安全前缀 ")]}\n"
        text = raw_response
        if text.startswith(")]}'"):
            text = text[4:]
        text = text.strip()

        # 提取第一个数组行（跳过长度前缀行）
        lines = text.split("\n")
        json_parts = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # 长度前缀行（纯数字）跳过
            if line.isdigit():
                i += 1
                continue
            if line.startswith("["):
                json_parts.append(line)
            i += 1

        if not json_parts:
            return {"success": False, "error": "无法解析响应", "raw": raw_response}

        # 解析主响应体
        try:
            data = json.loads(json_parts[0])
        except json.JSONDecodeError:
            return {"success": False, "error": "JSON 解析失败", "raw": json_parts[0]}

        # 查找 Yf4tfc RPC 的响应
        for item in data:
            if not isinstance(item, list) or len(item) < 2:
                continue
            if item[0] == "wrb.fr" and item[1] == FAUCET_RPC_ID:
                # item[2] = 成功时的结果 (JSON string)
                # item[5] = 错误信息 (如有)

                # 检查是否有错误
                if len(item) > 5 and item[5]:
                    error_info = item[5]
                    error_msg = FaucetClaimer._extract_error_message(error_info)
                    if "every 1 day" in error_msg.lower() or "try again" in error_msg.lower():
                        return {"success": False, "error": error_msg, "rate_limited": True}
                    return {"success": False, "error": error_msg}

                # 成功时解析结果
                if item[2]:
                    try:
                        result_data = json.loads(item[2])
                        return {"success": True, "data": result_data}
                    except (json.JSONDecodeError, TypeError):
                        return {"success": True, "data": item[2]}

                return {"success": False, "error": "空响应", "raw": str(item)}

        return {"success": False, "error": "未找到 RPC 响应", "raw": raw_response[:500]}

    @staticmethod
    def _extract_error_message(error_info) -> str:
        """从 batchexecute 错误结构中提取人类可读的错误消息"""
        if isinstance(error_info, list):
            # 递归搜索 LocalizedMessage
            for item in error_info:
                if isinstance(item, list):
                    for sub in item:
                        if isinstance(sub, list) and len(sub) >= 2:
                            if "LocalizedMessage" in str(sub[0]):
                                if isinstance(sub[1], list) and len(sub[1]) >= 2:
                                    return sub[1][1]
                    # 进一步递归
                    msg = FaucetClaimer._extract_error_message(item)
                    if msg:
                        return msg
                elif isinstance(item, str) and len(item) > 20:
                    return item
        return str(error_info)

    def claim(
        self,
        wallet_addresses: List[str],
        dry_run: bool = False,
    ) -> dict:
        """
        执行领水操作

        Args:
            wallet_addresses: 钱包地址列表
            dry_run: 如果为 True，只打印请求信息，不实际发送

        Returns:
            结果字典
        """
        # 1. 获取页面 token
        at_token, bl_token, f_sid = self._fetch_page_tokens()
        self.config.at_token = at_token
        self.config.bl_token = bl_token
        self.config.f_sid = f_sid

        # 2. 解码 reCAPTCHA
        logger.info("正在解码 reCAPTCHA Enterprise...")
        try:
            recaptcha_token = self.solver.solve(
                site_key=RECAPTCHA_SITE_KEY,
                page_url=RECAPTCHA_PAGE_URL,
                action="submit",
                min_score=0.3,
            )
        except RecaptchaSolverError as e:
            return {"success": False, "error": f"reCAPTCHA 解码失败: {e}"}

        # 3. 构造请求
        reqid = random.randint(100000, 999999)
        url = self._build_request_url(bl_token, f_sid, reqid)
        body = self._build_request_body(wallet_addresses, recaptcha_token, at_token)

        if dry_run:
            logger.info("=" * 60)
            logger.info("[DRY RUN] 以下是将要发送的请求:")
            logger.info(f"  URL: {url}")
            logger.info(f"  Body: {body[:200]}...")
            logger.info(f"  Wallets: {wallet_addresses}")
            logger.info(f"  reCAPTCHA token 长度: {len(recaptcha_token)}")
            logger.info("=" * 60)
            return {"success": True, "dry_run": True}

        # 4. 发送请求
        logger.info(f"正在向 faucet 发送领水请求 (钱包: {wallet_addresses})...")
        try:
            resp = self.session.post(url, data=body, timeout=30)
            logger.debug(f"HTTP 状态码: {resp.status_code}")
            logger.debug(f"响应内容: {resp.text[:500]}")
        except requests.RequestException as e:
            return {"success": False, "error": f"HTTP 请求失败: {e}"}

        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

        # 5. 解析响应
        result = self._parse_response(resp.text)
        return result

    def claim_all(self, dry_run: bool = False) -> List[dict]:
        """
        为配置中的所有钱包地址领水

        Args:
            dry_run: 是否为测试模式

        Returns:
            每个钱包的结果列表
        """
        results = []
        for i, addr in enumerate(self.config.wallet_addresses):
            logger.info(f"\n{'='*60}")
            logger.info(f"[{i+1}/{len(self.config.wallet_addresses)}] 领取钱包: {addr}")
            logger.info(f"{'='*60}")

            result = self.claim([addr], dry_run=dry_run)
            result["wallet"] = addr
            results.append(result)

            if result.get("success"):
                logger.info(f"✅ {addr}: 领水成功!")
                if result.get("data"):
                    logger.info(f"   返回数据: {result['data']}")
            else:
                logger.warning(f"❌ {addr}: {result.get('error', '未知错误')}")
                if result.get("rate_limited"):
                    logger.warning("   已触发频率限制")

            # 多个地址时间短暂等待
            if i < len(self.config.wallet_addresses) - 1:
                wait = random.uniform(2, 5)
                logger.info(f"等待 {wait:.1f}s 后继续...")
                time.sleep(wait)

        return results


# ============================================================
#  CLI 入口
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Google Cloud Web3 Hoodi ETH Faucet 自动领水",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用命令行参数
  python claim_faucet.py --wallet 0xAddr --cookies "SID=xxx; HSID=xxx; ..."

  # 从文件读取 cookies
  python claim_faucet.py --wallet 0xAddr --cookies-file cookies.txt

  # 多个钱包
  python claim_faucet.py --wallet 0xAddr1,0xAddr2 --cookies-file cookies.txt

  # 测试模式（不实际发送）
  python claim_faucet.py --wallet 0xAddr --cookies-file cookies.txt --dry-run

  # 使用 .env 配置文件
  python claim_faucet.py
        """,
    )
    parser.add_argument(
        "--wallet", "-w",
        help="钱包地址, 多个用逗号分隔",
    )
    parser.add_argument(
        "--cookies", "-c",
        help="Google cookie 字符串",
    )
    parser.add_argument(
        "--cookies-file", "-cf",
        help="从文件读取 Google cookie",
    )
    parser.add_argument(
        "--captcha-service",
        choices=["2captcha", "capsolver"],
        help="验证码解码服务 (默认: 2captcha)",
    )
    parser.add_argument(
        "--captcha-key",
        help="验证码服务的 API key",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="测试模式: 只打印请求信息，不实际领水",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 构建配置
    config = FaucetConfig()

    # CLI 参数覆盖 .env 配置
    if args.wallet:
        config.wallet_addresses = [a.strip() for a in args.wallet.split(",") if a.strip()]

    if args.cookies:
        config.google_cookies = args.cookies
    elif args.cookies_file:
        with open(args.cookies_file, "r", encoding="utf-8") as f:
            config.google_cookies = f.read().strip()

    if args.captcha_service:
        config.captcha_service = args.captcha_service
    if args.captcha_key:
        if config.captcha_service == "2captcha":
            config.twocaptcha_api_key = args.captcha_key
        else:
            config.capsolver_api_key = args.captcha_key

    # 验证配置
    errors = config.validate()
    if errors:
        logger.error("配置错误:")
        for err in errors:
            logger.error(f"  - {err}")
        logger.info("\n请通过命令行参数或 .env 文件提供配置。查看 --help 获取帮助。")
        return 1

    # 执行领水
    claimer = FaucetClaimer(config)
    results = claimer.claim_all(dry_run=args.dry_run)

    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("领水结果汇总:")
    logger.info("=" * 60)
    success_count = sum(1 for r in results if r.get("success"))
    for r in results:
        status = "✅" if r.get("success") else "❌"
        msg = r.get("error", "成功") if not r.get("success") else "成功"
        logger.info(f"  {status} {r.get('wallet', '?')}: {msg}")
    logger.info(f"\n成功: {success_count}/{len(results)}")

    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    exit(main())
