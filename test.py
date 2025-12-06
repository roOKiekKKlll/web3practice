from xauth import XAuth
import uuid


'''
https://x.com/i/oauth2/authorize?
response_type=code&
client_id=bFhSSkhWVDZXcHlqQnhCTWpXQlA6MTpjaQ&
redirect_uri=https%3A%2F%2Ftestnet.incentiv.io%2F%3Fprovider%3Dx&
scope=tweet.read+users.read+follows.read+offline.access&
state=c1a29977-3ad0-454f-bdc5-55a2a6f1938f&
code_challenge=5467010e804bc7705f96728c2786a58b611005dad5acf41138b7190b82e254c0&
code_challenge_method=plain


'''




def generate_random_uuid():
    """
    使用 uuid 模块生成一个基于随机数的 UUID (版本 4)。

    返回:
        str: 格式为 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx' 的 UUID 字符串。
    """
    # uuid.uuid4() 返回一个 UUID 对象
    new_uuid = uuid.uuid4()

    # 使用 str() 方法将其转换为标准的 UUID 字符串格式
    return str(new_uuid)






def main():
    # 创建XAuth实例
    x = XAuth("your valid xauth")

    try:
        # OAuth2认证测试
        params = {
            "code_challenge": "5467010e804bc7705f96728c2786a58b611005dad5acf41138b7190b82e254c0",
            "code_challenge_method": "plain",
            "client_id": "bFhSSkhWVDZXcHlqQnhCTWpXQlA6MTpjaQ",
            "redirect_uri": "https://testnet.incentiv.io/?provider=x",
            "response_type": "code",
            "scope": "tweet.read users.read follows.read offline.access",
            "state": generate_random_uuid()
        }
        auth_code = x.oauth2(params)
        print(f"OAuth2 认证码: {auth_code}")

        # OAuth1认证测试
        # oauth1_verifier = x.oauth1("lSgWPQAAAAABuWQYAAABk7sKZI0")
        # print(f"OAuth1 验证码: {oauth1_verifier}")

    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    main()
