# Fight.ID Automation Scripts

Fight.ID 平台自动化脚本集合，用于批量处理钱包登录、注册、游戏、绑定等操作。

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

## 📁 文件说明

### 核心脚本

| 脚本 | 功能 |
|------|------|
| `batch_login.py` | 批量登录获取 Token |
| `claim_fightid.py` | 批量 Claim FightID (注册账号) |
| `referral_job.py` | 批量使用推荐码注册 |
| `daily_game_new.py` | 每日沙袋游戏 + 链上 Mint |
| `batch_api_mint.py` | 批量 API Mint + BSC 合约调用 |
| `claim_point.py` | 领取 Streak Rewards |

### 钱包绑定脚本

| 脚本 | 功能 |
|------|------|
| `bind_apt.py` | 批量绑定 Aptos 钱包 |
| `bind_sol.py` | 批量绑定 Solana 钱包 |
| `batch_bind_email.py` | 批量绑定邮箱 |

### 工具脚本

| 脚本 | 功能 |
|------|------|
| `distribute_bnb.py` | 批量分发 BNB Gas |
| `fetch_referralcode.py` | 批量获取推荐码 |
| `clean_csv.py` | 清理 CSV 文件中的 NUL 字符 |
| `add_csv_email.py` | 合并邮箱信息到 CSV |

## 🔧 配置文件

### 1. wallet.txt (BSC 钱包私钥)

每行一个私钥：

```
0x1234567890abcdef...
0xabcdef1234567890...
```

### 2. tokens.csv (Token 映射)

```csv
wallet,token,更新时间
0x1234...,eyJhbGciOiJIUzI1NiIs...,2025-01-01 12:00:00
```

### 3. referral_info_main.csv (推荐码信息)

```csv
wallet,referralCode,referral_count
0x1234...,ABC123,5
```

### 4. 邮箱配置 (batch_bind_email.py)

通过环境变量设置：

```bash
export IMAP_PASSWORD="your_password"
export IMAP_SERVER="imap.example.com"
export IMAP_PORT="993"
```

### 5. 其他钱包私钥文件

- `apt_wallet.txt` - Aptos 私钥 (十六进制格式)
- `sol_wallet.txt` - Solana 私钥 (Base58 格式)
- `main_wallet.txt` - 主钱包私钥 (用于分发 Gas)

## 🚀 使用方法

### 1. 批量登录

```bash
python batch_login.py
```

### 2. 批量 Claim FightID

```bash
python claim_fightid.py
```

### 3. 每日游戏 + Mint

```bash
python daily_game_new.py
```

### 4. 批量绑定钱包

```bash
# 绑定 Aptos
python bind_apt.py

# 绑定 Solana
python bind_sol.py

# 绑定邮箱
python batch_bind_email.py
```

### 5. 分发 Gas

```bash
python distribute_bnb.py
```

## ⚠️ 注意事项

1. **私钥安全**：永远不要将私钥提交到 Git 仓库！
2. **环境变量**：敏感信息建议通过环境变量配置
3. **频率限制**：脚本已内置延迟，避免触发 API 限制
4. **Gas 费用**：确保钱包有足够的 BNB 支付 Gas

## 📝 输出文件

| 文件 | 说明 |
|------|------|
| `tokens.csv` | Token 记录 |
| `report.csv` | Claim 报告 |
| `game_results.csv` | 游戏结果 |
| `gas_distribution_report.csv` | Gas 分发报告 |
| `apt_bsc.csv` | APT 绑定结果 |
| `sol_bsc.csv` | SOL 绑定结果 |
| `game.log` | 游戏日志 |

## 🔒 安全提示

- 所有数据文件已添加到 `.gitignore`
- 敏感配置请使用环境变量
- 定期更换 Token 和密码
- 不要在公共网络运行脚本

## 📄 License

MIT License

