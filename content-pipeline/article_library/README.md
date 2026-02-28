# 📚 微信公众号文章管理库

统一管理所有生成的候选文章，支持审核状态标记，但不自动发布到公众号草稿箱。

## 核心功能

- ✅ **智能检索** - 用户请求时先查库，命中则直接返回（加速查询）
- ✅ **语义匹配** - 召回+筛选策略，找出最相关的3篇，随机选1
- ✅ **意图识别** - 调用Kimi判断用户是要查库还是生成新文章
- ✅ **集中存储** - 所有候选文章统一存储在文章库中
- ✅ **在线访问** - Web 界面查看文章库和文章详情
- ✅ **状态标记** - 候选/审核通过/未通过/需要修改
- ✅ **邮件通知** - 生成候选后自动发送访问链接
- ✅ **审核流程** - 回复邮件即可标记文章审核状态
- ✅ **不自动发布** - 审核通过仅作标记，不推送到草稿箱

## 快速开始

### 1. 启动文章库 Web 服务

```bash
cd /root/.openclaw/workspace/content-pipeline/article_library
./start_server.sh start
```

服务启动后访问：**http://154.9.252.35:8080/library**

### 2. 智能获取文章（推荐）

使用智能服务，自动判断查库还是生成：

```bash
# 智能判断（查库优先，未命中则生成）
cd /root/.openclaw/workspace/content-pipeline
python3 article_cli.py "给我一篇关于AI学习的文章"

# 强制生成新文章
cd /root/.openclaw/workspace/content-pipeline
python3 article_cli.py "帮我写关于时间管理的" --generate --count 10
```

流程：
1. **意图识别** - Kimi判断用户是查库还是生成
2. **智能检索** - 先查文章库，召回→筛选Top3→随机选1
3. **命中返回** - 返回缓存文章（加速！）
4. **未命中生成** - 生成10篇多样化文章→保存到库→返回
5. **发送通知** - 邮件发送文章库链接

### 3. 批量预生成文章（初始化文章库）

```python
from article_library.smart_service import generate_and_save

# 为核心主题预生成文章
result = generate_and_save("AI学习方法论", count=10, user_email="your@email.com")
result = generate_and_save("认知升级", count=10, user_email="your@email.com")
result = generate_and_save("AI工具提效", count=10, user_email="your@email.com")
```

### 4. 审核文章

通过邮件回复以下指令：

| 指令 | 说明 |
|------|------|
| `选候选1` / `选择候选2` | 标记指定候选为审核通过 |
| `都拒绝` / `重新生成` | 标记所有候选为未通过 |
| `修改xxx` | 标记为需要修改，附带建议 |
| `文章ID xxx 通过` | 直接指定文章ID审核通过 |

## 目录结构

```
article_library/
├── library.py           # 文章库核心模块
├── web_server.py        # Web 服务
├── email_notifier.py    # 邮件通知
├── pipeline_integration.py  # Pipeline集成
├── start_server.sh      # 启动脚本
├── library.db           # 数据库（自动创建）
└── articles/            # 文章文件存储
```

## CLI 工具使用

### 智能获取文章

```bash
cd /root/.openclaw/workspace/content-pipeline

# 智能判断（查库优先）
python3 article_cli.py "给我一篇关于AI学习的文章"

# 强制生成新文章
python3 article_cli.py "帮我写关于时间管理的" --generate

# 生成指定数量（1-10篇）
python3 article_cli.py "职业转型" --generate --count 5

# 发送通知邮件
python3 article_cli.py "AI工具" --generate --email "your@email.com"

# 查看文章库统计
python3 article_cli.py --stats

# 标记文章审核通过
python3 article_cli.py --mark ARTICLE_ID --status approved --notes "内容不错"

# 启动Web服务
python3 article_cli.py --serve
```

## API 使用

### 智能服务（一键查库或生成）

```python
from article_library.smart_service import get_article, SmartArticleService

# 简单用法
result = get_article("给我一篇关于AI学习的文章")

if result['success']:
    article = result['article']
    print(f"标题: {article['title']}")
    print(f"来源: {result['source']}")  # 'cache' 或 'generated'
    print(article['content'])
    
    # 如果有其他候选
    for alt in result['alternatives']:
        print(f"其他候选: {alt['title']}")

# 完整用法
service = SmartArticleService()
result = service.handle_request(
    user_input="给我一篇关于AI学习的文章",
    user_email="your@email.com",
    force_generate=False  # 是否强制生成
)
```

### 保存候选文章

```python
from article_library.library import ArticleLibrary

lib = ArticleLibrary()

# 保存单篇候选
article_id = lib.save_candidate(
    title="文章标题",
    topic="主题",
    content="文章内容",
    candidate_num=1,
    angle="文章角度",
    quality_score=8.5
)

# 批量保存
article_ids = lib.save_candidates_batch("主题", candidates_list)
```

### 标记审核状态

```python
# 审核通过
lib.mark_reviewed(article_id, 'approved', notes='内容质量不错')

# 拒绝
lib.mark_reviewed(article_id, 'rejected', notes='角度不够新颖')

# 需要修改
lib.mark_reviewed(article_id, 'revision_needed', notes='建议增加案例')
```

### 获取文章

```python
# 通过ID获取
article = lib.get_article(article_id)

# 通过分享token获取
article = lib.get_article_by_token(share_token)

# 列出文章
articles = lib.list_articles(status='candidate', limit=10)

# 获取统计
stats = lib.get_library_stats()
```

### 获取分享链接

```python
# 单篇文章链接
share_link = lib.get_share_link(article_id)
# 输出: http://154.9.252.35:8080/article/abc123

# 文章库链接
library_link = lib.get_library_link()
# 输出: http://154.9.252.35:8080/library
```

## 与 Pipeline 集成

已集成到 `pipeline_v31.py`，使用方式：

```bash
# 自动生成（自动主题）
python3 pipeline_v31.py

# 手动指定主题
python3 pipeline_v31.py --topic "AI学习方法论"
```

集成逻辑：
1. 生成候选文章
2. 调用 `library.save_candidates_batch()` 保存到文章库
3. 调用 `notifier.send_new_candidates_notification()` 发送邮件
4. 不再推送到微信公众号草稿箱

## 邮件通知

### 发送文章库访问链接

```python
from article_library.email_notifier import LibraryEmailNotifier

notifier = LibraryEmailNotifier()
notifier.send_library_access_link("your-email@example.com")
```

### 通知新候选文章

```python
notifier.send_new_candidates_notification(
    to_email="your-email@example.com",
    topic="AI学习方法论",
    article_ids=["id1", "id2", "id3"],
    candidate_count=3
)
```

### 发送审核确认

```python
notifier.send_review_confirmation(
    to_email="your-email@example.com",
    article_id="article_id",
    result="approved",  # approved/rejected/revision_needed
    notes="审核备注"
)
```

## 处理用户审核回复

```python
from article_library.pipeline_integration import handle_user_response

result = handle_user_response(
    response="选候选1",
    email="user@example.com"
)

print(result)
# {
#   'action': 'select_candidate',
#   'candidate_num': 1,
#   'article_id': 'xxx',
#   'success': True,
#   'message': '用户选择候选 1'
# }
```

## Web 界面

### 文章库首页
- 显示统计卡片（总数/候选/通过/已审核）
- 主题分布
- 最近文章列表
- 状态标签
- 分享链接

### 文章详情页
- 完整文章内容（Markdown渲染）
- 元数据（主题/角度/质量分/状态）
- 审核备注
- 返回文章库链接

## 数据存储

- **SQLite 数据库**: `article_library/library.db`
- **文章文件**: `article_library/articles/*.md`（带元数据头部）
- **分享Token**: 自动生成，用于URL访问

## 状态说明

| 状态 | 说明 |
|------|------|
| `candidate` | 候选文章，等待审核 |
| `reviewed_approved` | 审核通过（仅标记，未发布） |
| `reviewed_rejected` | 未通过 |
| `reviewed_revision_needed` | 需要修改 |

## 管理命令

```bash
# 启动服务
./start_server.sh start

# 停止服务
./start_server.sh stop

# 重启服务
./start_server.sh restart

# 查看状态
./start_server.sh status

# 查看日志
tail -f /tmp/article_library.log
```

## 配置

文章库位置：
- 数据库: `/root/.openclaw/workspace/content-pipeline/article_library/library.db`
- 文章文件: `/root/.openclaw/workspace/content-pipeline/article_library/articles/`
- Web 端口: `8080`

## 系统架构

```
用户请求
    │
    ▼
┌─────────────────────────────────────┐
│  意图识别 (Intent Recognizer)        │
│  - 调用Kimi判断: 查库 / 生成         │
└─────────────────────────────────────┘
    │
    ├─ 查库 ───────────────────────────┐
    │                                  ▼
    │              ┌─────────────────────────────────────┐
    │              │  检索引擎 (Search Engine)            │
    │              │  1. 召回: 关键词匹配 + 质量门槛       │
    │              │  2. 筛选: 语义相似度 + 质量 + 新鲜度   │
    │              │  3. 选出Top 3                        │
    │              │  4. 随机选1                          │
    │              └─────────────────────────────────────┘
    │                                  │
    │              命中 ◄───────────────┘
    │                │
    ▼                ▼
┌─────────────────────────────────────┐
│  多样化生成 (Diverse Generator)      │
│  - 10种不同角度各生成1篇             │
│  - 实战/深度/故事/数据/批判/趋势...  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  文章库 (Article Library)            │
│  - SQLite数据库                       │
│  - Markdown文件存储                   │
│  - 状态管理: 候选/审核通过/拒绝/修改   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  Web服务 / 邮件通知                  │
│  - 在线查看文章                       │
│  - 分享链接                          │
│  - 审核通知                          │
└─────────────────────────────────────┘
```

## 注意事项

1. **审核通过≠发布** - 审核通过只是标记状态，不会自动推送到公众号
2. **正式发布需手动** - 需要从文章库复制内容到公众号后台
3. **数据本地存储** - 所有数据存储在服务器本地，定期备份
4. **Web服务需保持运行** - 邮件中的链接依赖 Web 服务
5. **加速原理** - 预生成足够多的文章→用户查询时直接返回（无需等待生成）

## 初始化建议

为了充分发挥"加速查询"的优势，建议先预生成一批文章：

```python
# 为核心主题预生成文章
topics = [
    "AI学习方法论",
    "认知升级与思维模型", 
    "AI工具提效实战",
    "职业转型与机会挖掘",
    "AI时代的创造力培养",
    "信息筛选与知识管理"
]

for topic in topics:
    generate_and_save(topic, count=10)
    # 这样每个主题有10篇不同角度的文章
```

## 待完善功能

- [x] 文章搜索和筛选（语义相似度）
- [ ] 批量导出审核通过的文章
- [ ] 文章版本历史
- [ ] 与微信公众号API对接（正式发布时）
- [ ] 定时任务自动清理旧数据
- [ ] 使用真实Embedding API（替代简单hash）
- [ ] 热点主题自动预生成
