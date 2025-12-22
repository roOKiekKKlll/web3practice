# Binance 批量提现工具

基于 Binance API 的批量提现脚本，支持提现到多个不同地址。

## 功能特点

- ✅ 批量提现到多个不同地址
- ✅ 支持多种币种（USDT、BNB、ETH 等）
- ✅ 支持多种网络（BSC、TRX、ETH、ARB 等）
- ✅ **支持代理连接**（用于 IP 白名单验证）
- ✅ 模拟运行模式（不实际执行）
- ✅ 查看账户余额
- ✅ 查看币种支持的网络
- ✅ 查看提现历史
- ✅ 结果日志记录

## 安装

```bash
pip install -r requirements.txt
```

## 配置

### 1. API 密钥配置

复制示例配置文件并填入你的信息：

```bash
cp config.example.py config.py
```

然后编辑 `config.py`：

```python
API_KEY = "你的API_KEY"
API_SECRET = "你的API_SECRET"
WHITELIST_PROXY = "IP:PORT:USERNAME:PASSWORD"  # 白名单代理
```

> ⚠️ **重要提示**: 
> - 确保你的 API 密钥已开启提现权限
> - 设置正确的 IP 白名单
> - **不要将 config.py 提交到 Git**（已在 .gitignore 中忽略）

### 2. 代理配置（重要）

由于 Binance API 提现功能要求 IP 白名单验证，脚本支持通过代理连接。

代理格式支持两种：
- 带认证: `IP:PORT:USERNAME:PASSWORD`
- 无认证: `IP:PORT`

示例：
```python
# 带用户名密码的代理
WHITELIST_PROXY = "192.168.1.100:8080:username:password"

# 无认证代理
WHITELIST_PROXY = "192.168.1.100:8080"
```

### 3. 提现地址配置

复制示例文件并编辑：

```bash
cp withdraw_addresses.example.csv withdraw_addresses.csv
```

文件格式如下：

| 字段 | 说明 | 示例 |
|------|------|------|
| coin | 币种 | USDT, BNB, ETH |
| address | 提现地址 | 0x1234... |
| amount | 提现数量 | 100 |
| network | 网络（可选） | BSC, TRX, ETH, ARB |
| address_tag | 地址标签（可选） | memo、tag 等 |

示例：

```csv
coin,address,amount,network,address_tag
USDT,0x1234567890abcdef1234567890abcdef12345678,100,BSC,
USDT,TAbcdefghijklmnopqrstuvwxyz123456789,200,TRX,
BNB,0xabcdef1234567890abcdef1234567890abcdef12,0.5,BSC,
```

## 使用方法

### 测试代理连接

在执行任何操作前，建议先测试代理是否正常工作：

```bash
python batch_withdraw.py --test-proxy
# 或
python batch_withdraw.py -t
```

输出示例：
```
✓ 代理连接成功
  当前出口 IP: 45.120.80.124
```

### 查看账户余额

```bash
python batch_withdraw.py --balance
# 或
python batch_withdraw.py -b
```

### 查看币种支持的网络

```bash
python batch_withdraw.py --networks USDT
# 或
python batch_withdraw.py -n USDT
```

### 查看提现历史

```bash
python batch_withdraw.py --history
# 或
python batch_withdraw.py -H
```

### 模拟提现（不实际执行）

```bash
python batch_withdraw.py --withdraw --dry-run
# 或
python batch_withdraw.py -w -d
```

### 执行批量提现

```bash
python batch_withdraw.py --withdraw
# 或
python batch_withdraw.py -w
```

### 使用自定义地址文件

```bash
python batch_withdraw.py --withdraw --file my_addresses.csv
# 或
python batch_withdraw.py -w -f my_addresses.csv
```

### 设置提现间隔（默认 1 秒）

```bash
python batch_withdraw.py --withdraw --delay 2.0
```

## 常用网络代码

| 币种 | 网络代码 | 说明 |
|------|----------|------|
| USDT | BSC | BNB Smart Chain (BEP20) |
| USDT | TRX | Tron (TRC20) |
| USDT | ETH | Ethereum (ERC20) |
| USDT | ARB | Arbitrum |
| USDT | SOL | Solana |
| BNB | BSC | BNB Smart Chain |
| ETH | ETH | Ethereum |
| ETH | ARB | Arbitrum |

> 💡 使用 `--networks COIN` 命令查看具体币种支持的所有网络

## 输出文件

提现完成后，结果会保存到 `withdraw_results.csv` 文件中，包含：

- 时间戳
- 币种
- 地址
- 数量
- 网络
- 成功/失败状态
- API 响应

## 注意事项

1. **API 权限**: 确保 API 密钥已开启「允许提现」权限
2. **IP 白名单**: 建议设置 IP 白名单以提高安全性
3. **手续费**: 提现会收取网络手续费，请确保余额充足
4. **最小提现**: 每个币种/网络都有最小提现数量限制
5. **测试优先**: 建议先使用 `--dry-run` 模拟运行确认无误后再执行

## 错误排查

| 错误信息 | 可能原因 | 解决方案 |
|----------|----------|----------|
| Invalid API-key | API 密钥无效 | 检查 API_KEY 是否正确 |
| Signature verification failed | 签名错误 | 检查 API_SECRET 是否正确 |
| Withdraw is not allowed | 提现未授权 | 在 Binance 开启 API 提现权限 |
| IP not in whitelist | IP 不在白名单 | 使用 `--test-proxy` 确认代理 IP，并在 Binance 添加到白名单 |
| Insufficient balance | 余额不足 | 检查账户余额 |
| 代理连接失败 | 代理配置错误或不可用 | 检查 WHITELIST_PROXY 配置是否正确 |
| Connection timeout | 网络超时 | 检查代理是否可用，或增加超时时间 |

