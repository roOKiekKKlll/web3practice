"""
导出 Twitter Cookies 工具

使用方法：
1. 登录 Twitter 网站（使用 Chrome/Firefox）
2. 运行此脚本
3. 按照提示操作
"""

import json
from pathlib import Path

def main():
    print("=" * 60)
    print("Twitter Cookies 导出工具")
    print("=" * 60)
    print()
    
    print("⚠️  重要提示:")
    print("   Twitter 现在改名为 X，域名是 x.com")
    print("   必须从 x.com 导出 cookies，不是 twitter.com！")
    print()
    print("📋 导出步骤:")
    print()
    print("【Chrome 浏览器】")
    print("1. 访问 https://x.com 并登录 ⭐")
    print("2. 按 F12 打开开发者工具")
    print("3. 点击 'Application' 标签")
    print("4. 左侧选择 'Cookies' -> 'https://x.com' ⭐")
    print("5. 找到以下重要 Cookies:")
    print("   - auth_token")
    print("   - ct0")
    print("6. 复制这些 Cookie 的值")
    print()
    
    print("【Firefox 浏览器】")
    print("1. 访问 https://x.com 并登录 ⭐")
    print("2. 按 F12 打开开发者工具")
    print("3. 点击 'Storage' 标签")
    print("4. 展开 'Cookies' -> 'https://x.com' ⭐")
    print("5. 找到并复制 auth_token 和 ct0 的值")
    print()
    
    print("【最简单：使用浏览器插件（推荐）】")
    print("Chrome/Edge: 安装 'EditThisCookie' 或 'Cookie-Editor'")
    print("Firefox: 安装 'Cookie Quick Manager'")
    print("安装后:")
    print("  1. 访问并登录 https://x.com ⭐")
    print("  2. 点击插件图标")
    print("  3. 导出所有 x.com 的 cookies（JSON 格式）")
    print()
    print("⚠️ 关键: 必须是 x.com 的 cookies，不是 twitter.com！")
    print()
    
    print("=" * 60)
    print()
    
    choice = input("你想要:\n1. 手动输入 auth_token 和 ct0\n2. 粘贴完整的 cookies JSON\n请选择 (1/2): ").strip()
    
    cookies = {}
    
    if choice == "1":
        print("\n请输入 Cookie 值:")
        auth_token = input("auth_token = ").strip()
        ct0 = input("ct0 = ").strip()
        
        if not auth_token or not ct0:
            print("❌ 错误: Cookie 值不能为空")
            return
        
        cookies = {
            "auth_token": auth_token,
            "ct0": ct0
        }
        
    elif choice == "2":
        print("\n请粘贴完整的 cookies JSON（从浏览器插件导出）:")
        print("（粘贴后按 Enter，然后输入 'END' 并按 Enter）")
        
        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        
        json_str = "\n".join(lines)
        
        try:
            cookies_data = json.loads(json_str)
            
            # 如果是数组格式（从插件导出）
            if isinstance(cookies_data, list):
                print(f"检测到数组格式，共 {len(cookies_data)} 个 cookies")
                for cookie in cookies_data:
                    if isinstance(cookie, dict) and 'name' in cookie:
                        cookies[cookie['name']] = cookie.get('value', '')
            # 如果是对象格式
            elif isinstance(cookies_data, dict):
                print(f"检测到对象格式，共 {len(cookies_data)} 个 cookies")
                cookies = cookies_data
            
            print(f"✓ 解析到 {len(cookies)} 个 cookies")
            print(f"包含的 cookies: {', '.join(list(cookies.keys())[:10])}...")
            
            # 验证必要的 cookies
            required = ['auth_token', 'ct0']
            found = [c for c in required if c in cookies]
            missing = [c for c in required if c not in cookies]
            
            if found:
                print(f"✓ 找到必要的 cookies: {', '.join(found)}")
            if missing:
                print(f"⚠ 警告: 缺少 cookies: {', '.join(missing)}")
                print("  可能无法正常工作，建议重新导出完整的 cookies")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            return
    else:
        print("❌ 无效的选择")
        return
    
    # 保存 cookies
    output_file = "twitter_cookies.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2)
        
        print()
        print("=" * 60)
        print(f"✓ Cookies 已保存到: {output_file}")
        print("=" * 60)
        print()
        print("✅ 现在可以运行监控程序了:")
        print("   python run_monitor.py")
        print()
        
    except Exception as e:
        print(f"❌ 保存失败: {e}")

if __name__ == "__main__":
    main()

