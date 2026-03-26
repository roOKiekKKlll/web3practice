"""
reCAPTCHA Enterprise 解码模块
支持 2Captcha 和 CapSolver 两种服务
"""
import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class RecaptchaSolverError(Exception):
    """验证码解码失败"""
    pass


class RecaptchaSolver:
    """reCAPTCHA Enterprise v3 解码器"""

    def __init__(self, service: str, api_key: str):
        """
        Args:
            service: "2captcha" 或 "capsolver"
            api_key: 对应服务的 API Key
        """
        self.service = service.lower()
        self.api_key = api_key

        if self.service not in ("2captcha", "capsolver"):
            raise ValueError(f"不支持的验证码服务: {service}")

    def solve(self, site_key: str, page_url: str, action: str = "submit",
              min_score: float = 0.9, timeout: int = 120) -> str:
        """
        解码 reCAPTCHA Enterprise v3，返回 token

        Args:
            site_key: reCAPTCHA site key
            page_url: 目标页面 URL
            action: reCAPTCHA action 名称
            min_score: 最低期望分数
            timeout: 超时时间（秒）

        Returns:
            reCAPTCHA token 字符串
        """
        logger.info(f"使用 {self.service} 解码 reCAPTCHA Enterprise...")

        if self.service == "2captcha":
            return self._solve_2captcha(site_key, page_url, action, min_score, timeout)
        elif self.service == "capsolver":
            return self._solve_capsolver(site_key, page_url, action, min_score, timeout)

    def _solve_2captcha(self, site_key: str, page_url: str, action: str,
                        min_score: float, timeout: int) -> str:
        """使用 2Captcha 解码"""
        # 步骤1: 提交任务
        submit_url = "https://2captcha.com/in.php"
        params = {
            "key": self.api_key,
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
            "enterprise": 1,
            "invisible": 1,
            "json": 1,
        }

        logger.debug(f"提交验证码任务到 2Captcha...")
        resp = requests.get(submit_url, params=params, timeout=30)
        result = resp.json()

        if result.get("status") != 1:
            raise RecaptchaSolverError(f"2Captcha 提交失败: {result.get('request', 'unknown error')}")

        task_id = result["request"]
        logger.info(f"2Captcha 任务已提交, ID: {task_id}")

        # 步骤2: 轮询结果
        poll_url = "https://2captcha.com/res.php"
        poll_params = {
            "key": self.api_key,
            "action": "get",
            "id": task_id,
            "json": 1,
        }

        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(5)
            resp = requests.get(poll_url, params=poll_params, timeout=30)
            result = resp.json()

            if result.get("status") == 1:
                token = result["request"]
                logger.info(f"reCAPTCHA token 获取成功 (长度: {len(token)})")
                return token
            elif result.get("request") == "CAPCHA_NOT_READY":
                logger.debug("验证码尚未解决，继续等待...")
                continue
            else:
                raise RecaptchaSolverError(f"2Captcha 解码失败: {result.get('request', 'unknown error')}")

        raise RecaptchaSolverError(f"2Captcha 解码超时 ({timeout}s)")

    def _solve_capsolver(self, site_key: str, page_url: str, action: str,
                         min_score: float, timeout: int) -> str:
        """使用 CapSolver 解码"""
        # 步骤1: 创建任务
        create_url = "https://api.capsolver.com/createTask"
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "ReCaptchaV3EnterpriseTaskProxyLess",
                "websiteURL": page_url,
                "websiteKey": site_key,
                "pageAction": action,
                "minScore": min_score,
            }
        }

        logger.debug("提交验证码任务到 CapSolver...")
        resp = requests.post(create_url, json=payload, timeout=30)
        result = resp.json()

        if result.get("errorId", 1) != 0:
            raise RecaptchaSolverError(
                f"CapSolver 提交失败: {result.get('errorDescription', 'unknown error')}"
            )

        task_id = result["taskId"]
        logger.info(f"CapSolver 任务已提交, ID: {task_id}")

        # 步骤2: 轮询结果
        poll_url = "https://api.capsolver.com/getTaskResult"
        poll_payload = {
            "clientKey": self.api_key,
            "taskId": task_id,
        }

        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(3)
            resp = requests.post(poll_url, json=poll_payload, timeout=30)
            result = resp.json()

            status = result.get("status", "")
            if status == "ready":
                token = result["solution"]["gRecaptchaResponse"]
                logger.info(f"reCAPTCHA token 获取成功 (长度: {len(token)})")
                return token
            elif status == "processing":
                logger.debug("验证码尚未解决，继续等待...")
                continue
            else:
                raise RecaptchaSolverError(
                    f"CapSolver 解码失败: {result.get('errorDescription', 'unknown error')}"
                )

        raise RecaptchaSolverError(f"CapSolver 解码超时 ({timeout}s)")
