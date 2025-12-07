import requests
# 验证dc authtoken是否有效

test_headers = {
    "Authorization": "xxxxx",
    "User-Agent": "Mozilla/5.0"
}
r = requests.get("https://discord.com/api/v10/users/@me", headers=test_headers)
print(f"Token 验证状态码: {r.status_code}")