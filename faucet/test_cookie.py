import os
import re
import argparse
import requests
from dotenv import load_dotenv

from config import RECAPTCHA_PAGE_URL, DEFAULT_HEADERS

def parse_cookies(cookie_string: str) -> dict:
    """解析 cookie 字符串为字典"""
    cookies = {}
    for item in cookie_string.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            cookies[key.strip()] = value.strip()
    return cookies

def check_cookie_expired(cookie_string: str) -> bool:
    """
    检查 cookie 是否过期
    返回: True 表示过期或无效，False 表示有效
    """
    if not cookie_string:
        print("错误: cookie 字符串为空")
        return True
        
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    
    cookie_dict = parse_cookies(cookie_string)
    for name, value in cookie_dict.items():
        session.cookies.set(name, value, domain=".google.com")
        
    print(f"正在请求 {RECAPTCHA_PAGE_URL} 验证 cookie...")
    try:
        resp = session.get(RECAPTCHA_PAGE_URL, timeout=30)
        resp.raise_for_status()
        html = resp.text
        
        # 尝试提取 at token (XSRF)
        at_match = re.search(r'"SNlM0e":"([^"]+)"', html)
        if not at_match:
            at_match = re.search(r'WIZ_global_data.*?"SNlM0e"\s*:\s*"([^"]+)"', html, re.DOTALL)
            
        if not at_match:
            print("[\u274c] Cookie 已过期或无效: 无法从页面提取 XSRF token (at)。")
            return True
            
        at_token = at_match.group(1)
        print(f"[\u2705] Cookie 有效! 成功提取 XSRF token (at): {at_token[:20]}...")
        return False
        
    except requests.RequestException as e:
        print(f"[\u274c] 请求失败, 无法验证 cookie: {e}")
        return True

def main():
    parser = argparse.ArgumentParser(description="测试 Google Cookie 是否过期")
    parser.add_argument("--cookies", "-c", help="Google cookie 字符串")
    parser.add_argument("--cookies-file", "-cf", help="从文件读取 Google cookie")
    args = parser.parse_args()
    
    cookie_str = ""
    
    if args.cookies:
        cookie_str = args.cookies
    elif args.cookies_file:
        try:
            with open(args.cookies_file, "r", encoding="utf-8") as f:
                cookie_str = f.read().strip()
        except Exception as e:
            print(f"读取 cookie 文件失败: {e}")
            return
    else:
        # 尝试从 .env 读取
        load_dotenv()
        cookie_str = os.getenv("GOOGLE_COOKIES", "")
        if not cookie_str:
            print("请提供 cookie，通过 --cookies, --cookies-file 或在 .env 文件中设置 GOOGLE_COOKIES")
            return
            
    print("开始验证 Cookie...")
    is_expired = check_cookie_expired(cookie_str)
    if is_expired:
        print("-> 结论: Cookie 需要更新，请重新登录获取。")
    else:
        print("-> 结论: Cookie 正常可用。")

if __name__ == "__main__":
    main()
