# 微信公众号文章管理系统

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

面向保险行业的微信公众号内容生成、审核、推送一体化管理系统。支持智能选题、多用户管理、审核流程、微信草稿箱推送等功能。

## 🎯 功能概览

| 功能模块 | 描述 |
|---------|------|
| 📚 **文章库管理** | 集中存储文章，多维度标签，状态追踪 |
| 👤 **审核流程** | Web界面审核，意见批注，状态重置 |
| 🚀 **微信推送** | 一键推送到草稿箱，自动封面上传 |
| 🤖 **智能生成** | Kimi API内容生成，保险行业专用模板 |
| 👥 **多用户支持** | 用户隔离，个性化偏好 |

## 📁 项目结构

```
wechat-mp-content-system/
├── content-pipeline/article_library/  # 核心应用
│   ├── web_server.py                  # Flask主服务
│   ├── library.py                     # 数据库操作
│   ├── title_generator.py             # 标题生成器
│   ├── insurance_generator.py         # 保险文章生成
│   ├── wechat_draft_sync.py           # 微信草稿同步
│   ├── library.db                     # SQLite数据库
│   └── start_server.sh                # 启动脚本
├── config/                            # 配置文件
├── memory/                            # 工作记录
├── README.md                          # 本文件
├── requirements.txt                   # Python依赖
└── deploy.sh                          # 部署脚本
```

## 🚀 快速开始（5分钟启动）

### 1. 克隆项目

```bash
git clone https://github.com/zayme429/wechat-mp-content-system.git
cd wechat-mp-content-system
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量 / 密钥

```bash
# 方式1：使用 .env（推荐）
cp .env.example .env
# 编辑 .env 文件填入你的配置

# 方式2：直接设置环境变量
export WECHAT_APP_ID="your-app-id"
export WECHAT_APP_SECRET="your-app-secret"
```

另外，部分能力会读取 `content-pipeline/config/secrets.json`（用于本地开发/迁移时快速落地）。
你可以直接复制示例文件：

```bash
cp content-pipeline/config/secrets.example.json content-pipeline/config/secrets.json
# 编辑 content-pipeline/config/secrets.json 填入你的 key
```

**获取微信配置**：
1. 登录 [微信公众号后台](https://mp.weixin.qq.com/)
2. 开发 → 基本配置 → 获取 AppID 和 AppSecret
3. 设置服务器 IP 白名单

### 4. 初始化并启动

```bash
cd content-pipeline/article_library

# 初始化数据库
python3 -c "from library import ArticleLibrary; ArticleLibrary()"

# 启动服务
./start_server.sh
```

### 5. 访问系统

- 文章库管理：http://your-server-ip:8080/library
- 管理面板：http://your-server-ip:8080/dashboard

## 🔧 生产环境部署

### 使用部署脚本（推荐）

```bash
# 一键安装
./deploy.sh install

# 启动服务
./deploy.sh start

# 查看状态
./deploy.sh status

# 设置开机自启
./deploy.sh systemd
```

### Docker部署

```bash
# 创建配置
cp .env.example .env
# 编辑 .env 填入配置

# 构建并启动
docker-compose up -d
```

### 手动配置Systemd

```bash
sudo tee /etc/systemd/system/wechat-content.service << 'EOF'
[Unit]
Description=WeChat Content Management System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/wechat-mp-content-system/content-pipeline/article_library
Environment=WECHAT_APP_ID=your-app-id
Environment=WECHAT_APP_SECRET=your-app-secret
ExecStart=/usr/bin/python3 web_server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable wechat-content
sudo systemctl start wechat-content
```

## 🔄 迁移到新的服务器

### 方式1：使用Git（推荐）

```bash
# 新服务器
git clone https://github.com/zayme429/wechat-mp-content-system.git
cd wechat-mp-content-system
pip install -r requirements.txt

# 配置环境变量
export WECHAT_APP_ID="your-app-id"
export WECHAT_APP_SECRET="your-app-secret"

# 初始化数据库并启动
cd content-pipeline/article_library
python3 -c "from library import ArticleLibrary; ArticleLibrary()"
./start_server.sh
```

### 方式2：完整备份迁移

**在原服务器备份：**

```bash
cd /root/.openclaw/workspace
tar czvf wechat-content-backup.tar.gz \
  content-pipeline/article_library/library.db \
  content-pipeline/article_library/user_preferences.db \
  content-pipeline/article_library/articles/ \
  memory/
```

**在新服务器恢复：**

```bash
# 上传备份文件
cd /root/.openclaw/workspace
tar xzvf wechat-content-backup.tar.gz

# 安装依赖
pip install -r requirements.txt

# 启动服务
cd content-pipeline/article_library
./start_server.sh
```

### 方式3：Docker迁移

**导出镜像：**

```bash
docker save wechat-content:latest > wechat-content-image.tar
```

**在新服务器导入：**

```bash
docker load < wechat-content-image.tar
docker-compose up -d
```

## 📋 使用流程

### 1. 生成文章

系统会自动生成候选文章，或手动触发：

```python
from article_library.insurance_generator import generate_insurance_articles
articles = generate_insurance_articles("保险客户经营", count=5)
```

### 2. 审核文章

1. 访问 http://server:8080/library
2. 查看候选文章列表
3. 点击"审核"按钮
4. 选择：推送到草稿箱 / 不通过 / 需修改

### 3. 微信发布

1. 审核通过后自动推送到微信草稿箱
2. 登录微信公众号后台
3. 草稿箱 → 预览 → 确认发布

## ⚙️ 配置说明

### 必需配置（推送到公众号草稿箱）

| 配置项 | 说明 | 获取方式 |
|-------|------|---------|
| `WECHAT_APP_ID` | 微信公众号AppID | 公众号后台 → 开发 → 基本配置 |
| `WECHAT_APP_SECRET` | 微信公众号AppSecret | 同上 |

### 常用可选配置（按需开）

| 配置项 | 说明 | 建议配置方式 |
|-------|------|-------------|
| `ANTHROPIC_API_KEY` | Claude（LLM 生成/分析） | `.env` / 环境变量 |
| `OPENAI_API_KEY` | Embedding（向量召回，OpenAI兼容；可对接硅基流动） | `.env` / 环境变量 / `content-pipeline/config/secrets.local.json` |
| `OPENAI_BASE_URL` | Embedding base_url（例：`https://api.siliconflow.cn/v1`） | `.env` / 环境变量 / `content-pipeline/config/secrets.local.json` |
| `EMBEDDING_MODEL` | Embedding 模型名（硅基示例：`Qwen/Qwen3-Embedding-8B`） | `.env` / 环境变量 / `content-pipeline/config/secrets.local.json` |
| `EMBEDDING_DIM` | 仅 `text-embedding-3-*` 需要（其它模型可忽略） | `.env` / 环境变量 / `content-pipeline/config/secrets.local.json` |
| `KIMI_API_KEY` | Kimi/Moonshot（内容生成，OpenAI兼容） | `.env` / 环境变量 / `content-pipeline/config/secrets.local.json` |
| `KIMI_BASE_URL` | 生成服务的 base_url（可填你的 GPT Gateway） | `.env` / 环境变量 |
| `KIMI_MODEL` | 生成模型名（默认 `kimi-k2.5`） | `.env` / 环境变量 |
| `TAVILY_API_KEY` | Tavily（内容发现/检索） | `.env` / `content-pipeline/config/secrets.local.json` |
| `SENDCLAW_API_KEY` | SendClaw（审核邮件） | `.env` / `content-pipeline/config/secrets.local.json` |
| `SMTP_USER` / `SMTP_PASS` | SMTP 发信（审核通知等） | `content-pipeline/config/secrets.local.json` |
| `FLASK_PORT` | 服务端口 | `.env` / 环境变量 |
| `FLASK_HOST` | 监听地址 | `.env` / 环境变量 |

说明：仓库中不会提交真实 key；`content-pipeline/config/secrets.json` 已改成占位符。

### 配置文件

**内容策略** (`config/content_system.json`):
```json
{
  "article_types": ["客户经营", "获客", "转介绍"],
  "default_user": "insurance_agent",
  "generation": {
    "min_quality_score": 7.0,
    "max_candidates": 10
  }
}
```

## 🐛 常见问题

### Q: 推送失败，提示 "invalid media_id"

**A**: 封面图片上传失败
- 检查图片URL是否可访问
- 确保图片格式为JPEG
- 建议尺寸：1080x864

### Q: 标题超长推送失败

**A**: 微信标题限制64字节（约21个汉字）
- 系统会自动截断
- 可在 `title_generator.py` 中调整生成逻辑

### Q: 中文显示乱码

**A**: 已修复，确保使用最新代码
- 代码使用 `ensure_ascii=False` 处理中文

### Q: 如何更换AI模型？

**A**: 编辑 `insurance_generator.py`，修改 `_call_llm` 方法

## 📝 开发计划

- [ ] Docker Compose一键部署
- [ ] 多公众号支持
- [ ] 数据分析面板
- [ ] 封面图AI生成
- [ ] 定时自动发布

## 📄 许可证

MIT License

## 📞 支持

- GitHub Issues: https://github.com/zayme429/wechat-mp-content-system/issues
- Email: ZaymeShaw199742@outlook.com
