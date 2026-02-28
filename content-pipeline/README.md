# AI时代个人成长内容自动化系统

每日自动生成深度文章，聚焦AI时代个人学习成长与职业发展。

## 🎯 项目定位

**内容方向**：AI/科技领域深度文章  
**核心主题**：个人学习成长、适应时代变化、挖掘AI时代机会  
**内容风格**：有深入洞察，拒绝简单罗列口水文  
**目标读者**：关注AI发展的职场人士、学习者、创业者

## 📁 项目结构

```
content-pipeline/
├── config/
│   ├── pipeline.json           # 主配置（RSS源、关键词、内容策略）
│   └── prompts/                # AI提示词模板
│       ├── analyze_topic.md    # 选题分析提示词
│       └── write_article.md    # 文章撰写提示词
├── src/                        # 核心模块（待实现）
│   ├── fetcher/                # 数据采集
│   ├── processor/              # 内容处理
│   ├── generator/              # 文章生成
│   └── publisher/              # 发布模块
├── pipeline.py                 # 主流程脚本
├── scheduler.py                # 定时调度管理
├── memory/                     # 历史数据
│   └── published.json          # 已发布文章记录
├── logs/                       # 运行日志
├── output/                     # 生成的文章
└── README.md                   # 本文件
```

## 🚀 快速开始

### 1. 安装依赖

确保已安装：
- Python 3.8+
- OpenClaw 及相关 skills

```bash
# 安装内容采集skills
npx clawhub install news-aggregator-skill-2 --dir skills
npx clawhub install rss-digest --dir skills
npx clawhub install cron-scheduling --dir skills
```

### 2. 配置微信公众号

确保 `~/.wechatmp/config.json` 已配置：
```json
{
  "app_id": "your-app-id",
  "app_secret": "your-app-secret"
}
```

### 3. 配置内容策略

编辑 `config/pipeline.json`，调整：
- RSS订阅源
- 监控关键词
- 内容支柱主题
- 热点追踪设置

### 4. 手动运行测试

```bash
cd /root/.openclaw/workspace/content-pipeline
python scheduler.py run
```

### 5. 设置定时任务

```bash
python scheduler.py setup
```

按提示添加到 crontab。

## 🔄 工作流程

```
每日 8:00
    │
    ▼
┌─────────────────┐
│ 1. 采集热点资讯 │ ◄── RSS + 关键词 + 社交平台
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 2. AI分析选题   │ ◄── 找出最佳切入角度
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 3. AI撰写文章   │ ◄── 深度内容生成
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 4. 发布草稿箱   │ ◄── 微信公众号
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 5. 发送通知     │ ◄── 飞书/企微通知审核
└─────────────────┘
```

## 📝 内容质量标准

每篇文章必须满足：

- [ ] **深度优先**：深入分析，不浮于表面
- [ ] **案例支撑**：1-2个具体真实案例
- [ ] **独特视角**：不是人云亦云的跟风
- [ ] **实用建议**：提供可执行的行动方案
- [ ] **数据准确**：引用可靠来源的数据
- [ ] **不贩卖焦虑**：理性和建设性
- [ ] **1500-2000字**：足够阐述完整观点

## 🎨 内容支柱

六大核心主题（循环使用）：

1. **AI时代的学习方法论** - 如何高效学习AI相关知识
2. **认知升级与思维模型** - AI时代的思维方式转变
3. **AI工具提效实战** - 具体工具的使用技巧和案例
4. **职业转型与机会挖掘** - 新职业方向和发展路径
5. **AI时代的创造力培养** - 人 vs AI 的创造力差异
6. **信息筛选与知识管理** - 在海量信息中保持清醒

## 🛠️ 高级配置

### 自定义提示词

编辑 `config/prompts/` 下的模板：
- `analyze_topic.md` - 选题分析逻辑
- `write_article.md` - 文章撰写风格

### 调整发布频率

修改 `scheduler.py` 中的 cron 表达式：
```python
# 每天早上 8:00
cron_line = "0 8 * * * /usr/bin/python3 ..."

# 改为工作日早上 9:00
cron_line = "0 9 * * 1-5 /usr/bin/python3 ..."
```

### 查看运行状态

```bash
python scheduler.py status
```

### 查看日志

```bash
tail -f /root/.openclaw/workspace/content-pipeline/logs/pipeline.log
tail -f /root/.openclaw/workspace/content-pipeline/logs/cron.log
```

## 🔍 故障排查

### Pipeline执行失败

```bash
# 查看详细日志
cat logs/pipeline.log

# 手动调试
python pipeline.py
```

### 文章未生成

- 检查 RSS 源是否正常
- 检查网络连接
- 查看 `memory/published.json` 是否有重复主题过滤

### 发布到微信失败

- 检查 `~/.wechatmp/config.json` 配置
- 确认服务器 IP 在微信白名单
- 检查 wenyan-cli 是否安装

## 📊 效果追踪

记录指标：
- 每日生成文章数
- 选题角度多样性
- 阅读量/分享量（需要手动统计）
- 热点命中率

## 🚧 待完善功能

- [ ] RSS采集器实现
- [ ] 热点评分算法
- [ ] 去重和相似度检测
- [ ] 自动通知功能（飞书/企微）
- [ ] 封面图自动生成
- [ ] 发布数据分析

## 📝 更新日志

### 2026-02-26
- ✅ 项目初始化
- ✅ 核心架构设计
- ✅ AI提示词模板
- ✅ Pipeline框架搭建

---

**注意**：这是一个持续优化的项目，建议每周回顾生成内容质量，迭代调整提示词和策略。

---

## 🔄 完整工作流

```
每天 8:00 (定时任务)
    │
    ▼
┌────────────────────────────────────────────────┐
│ 1. RSS采集                                      │
│    - 机器之心、InfoQ、36氪等                    │
│    - 关键词匹配评分                             │
└────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────┐
│ 2. AI选题分析                                   │
│    - 分析热点价值                               │
│    - 选择最佳切入角度                           │
│    - 避免重复主题                               │
└────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────┐
│ 3. AI撰写文章                                   │
│    - 1500-2000字深度文章                        │
│    - 有案例、有数据、有洞察                     │
│    - 六大支柱主题循环                           │
└────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────┐
│ 4. 保存并通知审核                               │
│    - 保存到 output/article_YYYYMMDD.md          │
│    - 发送飞书/企微通知                          │
│    - 等待人工审核（30分钟）                     │
└────────────────────────────────────────────────┘
    │
    ├── 回复 "发布" ───────┐
    ├── 回复 "重新生成" ────┤
    └── 回复 "跳过" ────────┤
                          │
    ▼                     │
┌────────────────────────────────────────────────┐
│ 5. 发布到微信公众号草稿箱                       │
│    - 自动上传封面图                             │
│    - 格式化排版                                 │
│    - 生成草稿                                   │
└────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────┐
│ 6. 人工最终审核                                 │
│    - 登录微信公众号后台                         │
│    - 预览文章                                   │
│    - 确认发布/修改                              │
└────────────────────────────────────────────────┘
```

---

## 🎮 使用指南

### 首次运行

```bash
# 1. 测试Pipeline
python pipeline.py

# 2. 设置定时任务
crontab -e
# 添加: 0 8 * * * /root/.openclaw/workspace/content-pipeline/cron_job.sh

# 3. 查看审核指南
cat REVIEW_GUIDE.md
```

### 日常操作

```bash
# 查看今天生成的文章
cat output/article_$(date +%Y%m%d).md

# 手动审核并发布
python pipeline.py --review $(date +%Y%m%d) --action publish

# 跳过今日发布
python pipeline.py --review $(date +%Y%m%d) --action skip

# 查看状态
python scheduler.py status
```

### 审核指令（通过飞书/企微发送）

- `发布` - 确认发布到草稿箱
- `重新生成 [方向]` - 按新方向重新生成
- `跳过` - 今日不发布
- `查看文章` - 发送完整文章内容

---

## 📁 文件结构

```
content-pipeline/
├── config/
│   ├── pipeline.json              # 主配置
│   └── prompts/                   # AI提示词
│       ├── analyze_topic_simple.md
│       └── write_article_simple.md
├── src/
│   ├── fetcher/
│   │   └── rss_collector.py       # RSS采集
│   ├── generator/
│   │   └── content_generator.py   # AI生成
│   └── publisher/
│       └── (wechat publisher)     # 微信发布
├── output/                        # 生成的文章
├── memory/                        # 历史数据
├── logs/                          # 运行日志
├── pipeline.py                    # 主流程
├── cron_job.sh                    # 定时任务脚本
├── scheduler.py                   # 调度管理
├── README.md                      # 本文件
└── REVIEW_GUIDE.md               # 审核指南
```
