import csv
import requests
import time
import random
import threading
from queue import Queue
from loguru import logger


class FaucetClaimer:
    def __init__(self, yescaptcha_key: str):
        """
        初始化领水工具
        :param yescaptcha_key: YesCaptcha服务的client_key
        """
        self.yescaptcha_key = yescaptcha_key
        self.api_url = "https://faucet-go-production.up.railway.app/api/claim"
        self.site_key = "5b86452e-488a-4f62-bd32-a332445e2f51"
        self.headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }

    def _convert_proxy(self, proxy_str: str) -> dict:
        """转换代理格式：IP:端口:用户名:密码 -> requests可用的字典格式"""
        parts = proxy_str.split(':')
        if len(parts) != 4:
            raise ValueError(f"无效代理格式: {proxy_str}")

        ip, port, username, password = parts
        proxy_url = f"http://{username}:{password}@{ip}:{port}"
        return {
            "http": proxy_url,
            "https": proxy_url
        }

    def solve_hcaptcha(self) -> str:
        """通过YesCaptcha破解hCaptcha验证码"""
        task_url = "https://api.yescaptcha.com/createTask"
        task_data = {
            "clientKey": self.yescaptcha_key,
            "task": {
                "type": "HCaptchaTaskProxyless",
                "websiteURL": "https://faucet.campnetwork.xyz",
                "websiteKey": self.site_key
            }
        }

        try:
            response = requests.post(task_url, json=task_data, timeout=30)
            response.raise_for_status()
            task_id = response.json().get("taskId")
            if not task_id:
                raise ValueError("无法获取任务ID")

            # 轮询获取结果
            result_url = "https://api.yescaptcha.com/getTaskResult"
            start_time = time.time()
            while time.time() - start_time < 120:
                result_resp = requests.post(
                    result_url,
                    json={"clientKey": self.yescaptcha_key, "taskId": task_id},
                    timeout=10
                )
                result = result_resp.json()

                if result.get("status") == "ready":
                    return result["solution"]["gRecaptchaResponse"]
                elif result.get("status") == "failed":
                    raise ValueError(f"验证码识别失败: {result.get('errorDescription')}")

                time.sleep(2)

            raise TimeoutError("验证码识别超时")
        except Exception as e:
            logger.error(f"验证码服务异常: {str(e)}")
            raise

    def claim_faucet(self, wallet_address: str, proxy_str: str) -> bool:
        """
        调用领水API
        :param wallet_address: 钱包地址
        :param proxy_str: 代理字符串（格式：IP:端口:用户名:密码）
        :return: 是否成功
        """
        try:
            # 1. 转换代理格式
            proxies = self._convert_proxy(proxy_str)

            # 2. 获取验证码token
            captcha_token = self.solve_hcaptcha()
            self.headers["h-captcha-response"] = captcha_token
            payload = {"address": wallet_address}

            # 3. 发送请求
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                proxies=proxies,
                timeout=30
            )

            if response.status_code == 200:
                logger.success(f"成功 | 地址: {wallet_address[:8]}... | 代理: {proxy_str.split(':')[0]}")
                return True
            else:
                logger.error(f"失败 | HTTP {response.status_code} | 响应: {response.text}")
                return False

        except Exception as e:
            logger.error(f"异常 | 代理 {proxy_str.split(':')[0]} 错误: {str(e)}")
            return False


def load_wallets_from_csv(file_path: str) -> list:
    """从CSV读取钱包地址和代理"""
    wallets = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get("address") and row.get("proxy"):
                wallets.append({
                    "address": row["address"].strip(),
                    "proxy": row["proxy"].strip()
                })
    return wallets


def worker(claimer: FaucetClaimer, task_queue: Queue):
    """工作线程：处理队列中的领水任务"""
    while not task_queue.empty():
        task = task_queue.get()
        claimer.claim_faucet(task["address"], task["proxy"])
        task_queue.task_done()
        time.sleep(random.uniform(5, 10))  # 随机间隔5-10秒


if __name__ == "__main__":
    # 配置参数
    YESCAPTCHA_KEY = "你自己的apikey"  # 替换为实际密钥
    CSV_FILE = "wallet.csv"  # CSV文件路径

    # 初始化
    logger.add("faucet.log", rotation="10 MB")  # 日志记录到文件
    wallets = load_wallets_from_csv(CSV_FILE)
    if not wallets:
        raise ValueError("CSV文件中未找到有效的钱包地址和代理")

    claimer = FaucetClaimer(YESCAPTCHA_KEY)
    task_queue = Queue()

    # 填充任务队列
    for wallet in wallets:
        task_queue.put(wallet)

    # 启动多线程（建议3-5个线程）
    threads = []
    for _ in range(3):
        thread = threading.Thread(target=worker, args=(claimer, task_queue))
        thread.start()
        threads.append(thread)

    # 等待所有任务完成
    task_queue.join()
    for thread in threads:
        thread.join()

    logger.info("所有任务处理完成")