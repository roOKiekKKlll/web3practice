#!/usr/bin/env python3
"""
多账号 Cookies 管理工具
支持添加、删除、启用/禁用账号
"""

import json
from pathlib import Path

COOKIES_FILE = "twitter_cookies.json"

def load_cookies():
    """加载 cookies 配置"""
    if not Path(COOKIES_FILE).exists():
        return {"accounts": []}
    
    with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 兼容旧格式
    if 'accounts' not in data:
        # 转换为新格式
        return {
            "accounts": [{
                "name": "默认账号",
                "auth_token": data['auth_token'],
                "ct0": data['ct0'],
                "enabled": True
            }]
        }
    
    return data

def save_cookies(data):
    """保存 cookies 配置"""
    with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ 已保存到 {COOKIES_FILE}")

def list_accounts():
    """列出所有账号"""
    data = load_cookies()
    accounts = data.get('accounts', [])
    
    if not accounts:
        print("❌ 没有任何账号")
        return
    
    print("\n" + "=" * 60)
    print("当前账号列表:")
    print("=" * 60)
    
    for idx, account in enumerate(accounts, 1):
        status = "✓ 启用" if account.get('enabled', True) else "✗ 禁用"
        name = account.get('name', f'账号{idx}')
        token_preview = account['auth_token'][:20] + "..."
        
        print(f"\n[{idx}] {name} ({status})")
        print(f"    auth_token: {token_preview}")
        print(f"    ct0: {account['ct0'][:20]}...")
    
    print("\n" + "=" * 60)

def add_account():
    """添加新账号"""
    print("\n" + "=" * 60)
    print("添加新账号")
    print("=" * 60)
    
    name = input("账号名称（例如：小号1）: ").strip()
    if not name:
        name = f"账号{len(load_cookies()['accounts']) + 1}"
    
    print("\n请从浏览器（https://x.com）复制以下 cookies:")
    auth_token = input("auth_token: ").strip()
    ct0 = input("ct0: ").strip()
    
    if not auth_token or not ct0:
        print("❌ auth_token 和 ct0 不能为空！")
        return
    
    data = load_cookies()
    data['accounts'].append({
        "name": name,
        "auth_token": auth_token,
        "ct0": ct0,
        "enabled": True
    })
    
    save_cookies(data)
    print(f"✓ 账号 '{name}' 已添加")

def remove_account():
    """删除账号"""
    list_accounts()
    
    try:
        idx = int(input("\n请输入要删除的账号编号: ")) - 1
        data = load_cookies()
        accounts = data['accounts']
        
        if 0 <= idx < len(accounts):
            removed = accounts.pop(idx)
            save_cookies(data)
            print(f"✓ 已删除账号: {removed['name']}")
        else:
            print("❌ 无效的编号")
    except ValueError:
        print("❌ 请输入数字")

def toggle_account():
    """启用/禁用账号"""
    list_accounts()
    
    try:
        idx = int(input("\n请输入要切换状态的账号编号: ")) - 1
        data = load_cookies()
        accounts = data['accounts']
        
        if 0 <= idx < len(accounts):
            accounts[idx]['enabled'] = not accounts[idx].get('enabled', True)
            status = "启用" if accounts[idx]['enabled'] else "禁用"
            save_cookies(data)
            print(f"✓ 账号 '{accounts[idx]['name']}' 已{status}")
        else:
            print("❌ 无效的编号")
    except ValueError:
        print("❌ 请输入数字")

def migrate_from_old():
    """从旧格式迁移"""
    if not Path(COOKIES_FILE).exists():
        print("❌ 找不到 cookies 文件")
        return
    
    with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'accounts' in data:
        print("✓ 已经是新格式，无需迁移")
        return
    
    # 转换为新格式
    new_data = {
        "accounts": [{
            "name": "默认账号",
            "auth_token": data['auth_token'],
            "ct0": data['ct0'],
            "enabled": True
        }]
    }
    
    # 备份旧文件
    backup_file = "twitter_cookies.json.backup"
    Path(COOKIES_FILE).rename(backup_file)
    print(f"✓ 旧文件已备份到 {backup_file}")
    
    save_cookies(new_data)
    print("✓ 已迁移到新格式")

def main():
    """主菜单"""
    while True:
        print("\n" + "=" * 60)
        print("Twitter Cookies 多账号管理")
        print("=" * 60)
        print("1. 查看所有账号")
        print("2. 添加新账号")
        print("3. 删除账号")
        print("4. 启用/禁用账号")
        print("5. 从旧格式迁移")
        print("0. 退出")
        print("=" * 60)
        
        choice = input("\n请选择操作: ").strip()
        
        if choice == '1':
            list_accounts()
        elif choice == '2':
            add_account()
        elif choice == '3':
            remove_account()
        elif choice == '4':
            toggle_account()
        elif choice == '5':
            migrate_from_old()
        elif choice == '0':
            print("再见！")
            break
        else:
            print("❌ 无效的选择")

if __name__ == "__main__":
    main()

