# Fight.ID Clean CSV Script
# 清理 CSV 文件中的 NUL 字符

import os


def clean_csv(filename="referral_info_main.csv"):
    if not os.path.exists(filename):
        print(f"文件未找到: {filename}")
        return

    try:
        # 1. 以二进制模式读取整个文件内容
        with open(filename, 'rb') as f:
            content = f.read()

        # 2. 移除所有 NUL 字节 (b'\x00')
        cleaned_content = content.replace(b'\x00', b'')

        # 3. 将清理后的内容写回文件 (以UTF-8编码)
        with open(filename, 'wb') as f:
            f.write(cleaned_content)

        print(f"✅ 文件 '{filename}' 清理完成，所有 NUL 字符已被移除。")

    except Exception as e:
        print(f"❌ 清理文件时发生错误: {e}")


if __name__ == "__main__":
    # 清理您的目标文件
    clean_csv("referral_info_main.csv")

    # 如果您不确定是哪个文件有问题，也可以清理私钥文件
    clean_csv("referral_wallet.txt")

