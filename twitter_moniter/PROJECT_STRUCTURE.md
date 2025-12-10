# 项目结构

```
twitter_moniter/
│
├── 🚀 主程序
│   ├── run_monitor_final.py          # 启动监控
│   └── twitter_monitor_requests.py   # 核心监控逻辑（多账号轮询）
│
├── ⚙️ 配置
│   ├── config.py                     # 监控配置（用户、间隔、微信等）
│   └── twitter_cookies.json          # Cookies 配置（多账号）
│
├── 🔐 账号管理
│   ├── manage_cookies.py             # 多账号管理工具（推荐）
│   └── export_cookies.py             # 单账号导出工具
│
├── 📱 微信推送
│   ├── wechat_push.py               # Server酱推送（个人微信）
│   └── wechat_group_bot.py          # 微信群机器人（Windows）
│
├── 📚 文档
│   ├── README.md                    # 完整说明
│   └── QUICKSTART.md                # 快速开始
│
├── 📦 其他
│   ├── requirements.txt             # Python 依赖
│   ├── .gitignore                   # Git 忽略配置
│   └── monitor_data/                # 历史数据（自动生成）
│
└── 🚫 忽略（.gitignore）
    ├── venv/                        # 虚拟环境
    ├── __pycache__/                 # Python 缓存
    ├── twitter_cookies.json         # 敏感信息
    └── monitor_data/                # 历史数据
```

## 核心文件说明

### 必需文件（11 个）
1. **run_monitor_final.py** - 主程序入口
2. **twitter_monitor_requests.py** - 监控核心（637行）
3. **config.py** - 用户配置
4. **twitter_cookies.json** - Cookies（需创建）
5. **manage_cookies.py** - 账号管理
6. **export_cookies.py** - 导出工具
7. **wechat_push.py** - 微信推送
8. **wechat_group_bot.py** - 群机器人
9. **requirements.txt** - 依赖列表
10. **README.md** - 使用说明
11. **.gitignore** - Git配置

### 可选文件
- **QUICKSTART.md** - 快速参考
- **PROJECT_STRUCTURE.md** - 本文件

## 代码量统计

```
核心代码:   ~800 行
配置代码:   ~300 行
文档:       ~200 行
-----------------------
总计:       ~1300 行
```

## 使用流程

```
开始
 │
 ├─> 安装: pip install -r requirements.txt
 │
 ├─> 配置账号:
 │    └─> python manage_cookies.py (添加 2-3 个小号)
 │
 ├─> 配置监控:
 │    └─> 编辑 config.py (用户、SendKey)
 │
 └─> 运行: python run_monitor_final.py
```

---

**项目已精简完成！** ✨

