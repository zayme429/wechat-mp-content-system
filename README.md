# 微信公众号文章管理系统 (wechat-mp-content-system)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

一个完整的微信公众号内容生成、审核、推送一体化管理系统。面向保险行业（可扩展至其他领域），支持智能选题、多用户管理、审核流程、微信草稿箱推送等功能。

## ✨ 核心功能

### 1. 文章库管理
- 📚 集中存储文章（不在微信草稿箱，便于管理）
- 🏷️ 多维度标签（主题、角度、质量分）
- 📊 文章状态追踪（候选、审核中、已发布）
- 🔍 智能检索（语义搜索 + 关键词过滤）

### 2. 审核流程
- 👤 Web界面审核
- ✍️ 审核意见批注
- 🔄 状态重置（可退回候选）
- 📱 推送状态管理（文章库→草稿箱→正式推送）

### 3. 微信集成
- 🚀 一键推送到微信草稿箱
- 🖼️ 自动封面上传
- 📝 Markdown转HTML
- 🔄 草稿箱同步检测

### 4. 智能生成
- 🤖 Kimi API 内容生成
- 🎯 保险行业专用模板
- 📐 10种写作角度（故事案例、话术实战、情感连接等）
- ✨ 智能标题生成（符合公众号风格）

### 5. 多用户支持
- 👥 用户隔离（保险代理人/科技爱好者）
- 🎨 个性化偏好
- 📈 审核历史学习

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                     前端界面 (Web)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ 文章库管理   │  │ 审核页面     │  │ 用户偏好设置     │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Flask Web Server                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ 文章管理API  │  │ 审核流程API  │  │ 微信推送API      │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  SQLite DB │  │  WeChat API│  │  Kimi API  │
    │ (文章数据)  │  │ (草稿箱)   │  │ (内容生成) │
    └────────────┘  └────────────┘  └────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.9+
- SQLite 3
- 服务器：建议 2核4G 以上
- 网络：需访问微信API（国内服务器更佳）

### 1. 克隆项目

```bash
git clone https://github.com/zayme429/wechat-mp-content-system.git
cd wechat-mp-content-system/content-pipeline/article_library
```

### 2. 安装依赖

```bash
pip install flask requests sqlite3
```

### 3. 配置微信API

编辑 `~/.openclaw/workspace/TOOLS.md` 或设置环境变量：

```bash
export WECHAT_APP_ID="your-app-id"
export WECHAT_APP_SECRET="your-app-secret"
```

**获取方式**：
1. 登录 [微信公众号后台](https://mp.weixin.qq.com/)
2. 开发 → 基本配置 → 获取 AppID 和 AppSecret
3. 设置服务器 IP 白名单

### 4. 配置Kimi API（内容生成）

编辑 `content-pipeline/config/secrets.json`：

```json
{
  "kimi_api_key": "your-kimi-api-key"
}
```

### 5. 初始化数据库

```bash
cd content-pipeline/article_library
python -c "from library import ArticleLibrary; lib = ArticleLibrary(); print('DB initialized')"
```

### 6. 启动服务

```bash
./start_server.sh
```

服务启动后访问：
- 📚 文章库：http://your-server-ip:8080/library
- 📊 管理面板：http://your-server-ip:8080/dashboard

### 7. 设置开机自启（可选）

```bash
# 添加到 systemd
sudo tee /etc/systemd/system/wechat-content.service << 'EOF'
[Unit]
Description=WeChat Content Management System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw/workspace/content-pipeline/article_library
ExecStart=/root/.openclaw/workspace/content-pipeline/article_library/start_server.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable wechat-content
sudo systemctl start wechat-content
```

## ⚙️ 配置说明

### 配置文件结构

```
content-pipeline/
├── config/
│   ├── content_system.json      # 内容策略配置
│   ├── secrets.json             # API密钥（不提交git）
│   └── prompts/                 # AI提示词模板
│       ├── analyze_topic.md
│       └── write_article.md
└── article_library/
    ├── library.db               # SQLite数据库
    └── user_preferences.db      # 用户偏好数据
```

### 关键配置项

#### 1. 内容策略 (`config/content_system.json`)

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

#### 2. 微信配置（环境变量）

```bash
# ~/.bashrc 或 ~/.zshrc
export WECHAT_APP_ID="wx5c6f2e9b5734ddd5"
export WECHAT_APP_SECRET="baf071b9ca8e805992a26111c552b9f9"
```

#### 3. 标题生成器 (`article_library/title_generator.py`)

可自定义标题模板和词汇库，调整生成风格。

## 📋 使用流程

### 日常操作流程

```
1. 生成文章
   └─ 系统每日自动生成候选文章（或手动触发）

2. 审核文章
   └─ 访问 /library 查看候选文章
   └─ 点击"审核"按钮
   └─ 选择：推送/不通过/需修改

3. 推送微信
   └─ 审核通过后点击"推送到草稿箱"
   └─ 系统自动上传封面 + 转换HTML
   └─ 在微信后台预览确认

4. 发布文章
   └─ 登录微信公众号后台
   └─ 草稿箱 → 预览 → 群发
```

### 首次使用建议

1. **导入现有文章**（如有）
   ```bash
   python wechat_draft_sync.py
   ```

2. **生成测试文章**
   ```bash
   cd content-pipeline/article_library
   python insurance_generator.py
   ```

3. **测试推送流程**
   - 选择一篇候选文章
   - 点击审核 → 推送到草稿箱
   - 检查微信后台是否正常显示

## 🔄 迁移指南

### 场景1：迁移到新服务器

```bash
# 1. 在原服务器备份数据
cd /root/.openclaw/workspace
tar czvf backup.tar.gz content-pipeline/

# 2. 传输到新服务器
scp backup.tar.gz new-server:/tmp/

# 3. 在新服务器恢复
ssh new-server
cd /root/.openclaw/workspace
tar xzvf /tmp/backup.tar.gz

# 4. 重新配置环境变量
export WECHAT_APP_ID="your-app-id"
export WECHAT_APP_SECRET="your-app-secret"

# 5. 启动服务
cd content-pipeline/article_library
./start_server.sh
```

### 场景2：Docker部署（推荐）

创建 `Dockerfile`：

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装依赖
RUN pip install flask requests

# 复制项目
COPY content-pipeline/article_library /app/
COPY content-pipeline/config /app/config

# 暴露端口
EXPOSE 8080

# 启动
CMD ["python", "web_server.py"]
```

创建 `docker-compose.yml`：

```yaml
version: '3'
services:
  wechat-content:
    build: .
    ports:
      - "8080:8080"
    environment:
      - WECHAT_APP_ID=${WECHAT_APP_ID}
      - WECHAT_APP_SECRET=${WECHAT_APP_SECRET}
      - KIMI_API_KEY=${KIMI_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: always
```

部署：

```bash
# 1. 创建 .env 文件
cat > .env << 'EOF'
WECHAT_APP_ID=your-app-id
WECHAT_APP_SECRET=your-app-secret
KIMI_API_KEY=your-kimi-key
EOF

# 2. 启动
docker-compose up -d

# 3. 查看日志
docker-compose logs -f
```

### 场景3：多实例部署

如需部署多个实例（如不同公众号）：

```bash
# 实例1：保险号
cd /opt/wechat-insurance
export WECHAT_APP_ID="insurance-app-id"
export PORT=8081
./start_server.sh

# 实例2：科技号
cd /opt/wechat-tech
export WECHAT_APP_ID="tech-app-id"
export PORT=8082
./start_server.sh
```

使用 Nginx 反向代理：

```nginx
server {
    listen 80;
    server_name insurance.example.com;
    
    location / {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
    }
}

server {
    listen 80;
    server_name tech.example.com;
    
    location / {
        proxy_pass http://localhost:8082;
        proxy_set_header Host $host;
    }
}
```

## 📁 项目结构

```
wechat-mp-content-system/
├── content-pipeline/
│   ├── article_library/           # 核心模块
│   │   ├── library.py             # 数据库操作
│   │   ├── web_server.py          # Flask Web服务
│   │   ├── title_generator.py     # 标题生成器
│   │   ├── insurance_generator.py # 保险文章生成
│   │   ├── wechat_draft_sync.py   # 微信草稿同步
│   │   ├── push_logger.py         # 推送日志
│   │   ├── library.db             # SQLite数据库
│   │   └── start_server.sh        # 启动脚本
│   ├── config/                    # 配置文件
│   │   ├── content_system.json
│   │   ├── secrets.json           # API密钥（gitignore）
│   │   └── prompts/               # AI提示词
│   └── logs/                      # 运行日志
├── memory/                        # 工作记录
│   └── 2026-02-28.md
├── README.md                      # 本文件
└── requirements.txt               # Python依赖
```

## 🔧 常见问题

### Q1: 推送失败提示 "invalid media_id"

**原因**：封面图片上传失败或格式不符
**解决**：
- 检查图片URL是否可访问
- 确保图片为JPEG格式
- 建议尺寸：1080x864

### Q2: 标题超长推送失败

**原因**：微信标题限制64字节（约21个汉字）
**解决**：标题生成器会自动截断，可在 `title_generator.py` 中调整

### Q3: 中文显示乱码

**原因**：JSON编码问题
**解决**：已修复，确保使用 `ensure_ascii=False` 编码

### Q4: 如何更换AI模型？

编辑 `src/generator/content_generator.py`，修改 `_call_llm` 方法。

## 📝 开发计划

- [ ] Docker 一键部署
- [ ] 多公众号支持
- [ ] 数据分析面板
- [ ] 封面图AI生成
- [ ] 定时自动发布
- [ ] 文章效果追踪

## 📄 许可证

MIT License

## 🤝 贡献指南

欢迎提交 Issue 和 PR！

## 📞 联系方式

- GitHub Issues: https://github.com/zayme429/wechat-mp-content-system/issues
- Email: ZaymeShaw199742@outlook.com

---

**部署提示**：生产环境建议使用 Docker + Nginx + HTTPS，确保数据安全。
