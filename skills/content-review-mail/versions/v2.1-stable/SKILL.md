---
name: content-review-mail
description: |
  内容审核邮件系统 - 通过邮件实现内容审核的双向通信。
  支持：发送多候选审核邮件、解析用户回复指令、自动执行操作、邮件对话讨论。
  适用于：内容生成后的审核流程、多候选选择、迭代修改讨论。
---

# Content Review Mail

通过邮件实现内容审核的双向通信系统。

## 功能特性

- ✅ **发送审核邮件** - 发送包含多候选文章的HTML邮件
- ✅ **解析回复指令** - 自动识别发布/重新生成/修改/跳过等指令
- ✅ **邮件双向对话** - 支持多轮邮件讨论和迭代
- ✅ **状态管理** - 记录待审核项目、处理历史
- ✅ **灵活配置** - 支持Gmail/Outlook/163等主流邮箱

## 依赖

- Python 3.8+
- SMTP 发送：任意邮箱（163/Gmail/Outlook）
- 邮件接收（二选一）：
  - IMAP/POP3 协议（需要服务器支持）
  - [ForwardEmail](FORWARDEMAIL_GUIDE.md) Webhook（推荐，绕过IMAP限制）

## 快速开始

### 1. 配置邮箱

编辑 `config/config.json`：

```json
{
  "imap": {
    "host": "imap.gmail.com",
    "port": 993,
    "user": "your-email@gmail.com",
    "pass": "your-app-password",
    "tls": true,
    "mailbox": "INBOX"
  },
  "smtp": {
    "host": "smtp.gmail.com",
    "port": 587,
    "secure": false,
    "user": "your-email@gmail.com",
    "pass": "your-app-password",
    "from": "your-email@gmail.com"
  },
  "review": {
    "check_interval_minutes": 5,
    "auto_reply": true,
    "save_history": true,
    "default_recipient": "your-receive-email@example.com"
  }
}
```

### 2. 授权码获取

**Gmail：**
1. 开启两步验证
2. 生成应用专用密码
3. 使用应用密码代替邮箱密码

**QQ邮箱：**
1. 设置 → 账户 → 开启IMAP/SMTP服务
2. 获取授权码（16位）

**163邮箱：**
1. 设置 → POP3/SMTP/IMAP
2. 开启IMAP/SMTP服务
3. 获取授权码

### 3. 使用

#### 发送审核邮件

```python
from content_review_mail import ContentReviewMail

crm = ContentReviewMail()

# 准备候选文章
candidates = [
    {
        'topic': '文章标题1',
        'angle_type': '实战派',
        'quality_score': 8.5,
        'uniqueness_score': 7.5,
        'word_count': 1500,
        'content': '文章内容...'
    },
    {
        'topic': '文章标题2',
        'angle_type': '深度派',
        'quality_score': 7.5,
        'uniqueness_score': 8.5,
        'word_count': 1800,
        'content': '文章内容...'
    }
]

# 发送审核邮件
crm.send_review_email(
    to='reviewer@example.com',
    subject='📄 内容审核 - 20260226 (2个候选)',
    candidates=candidates,
    article_date='20260226'
)
```

#### 检查回复

```python
# 检查新邮件
emails = crm.check_new_emails()

for email in emails:
    # 判断是否是审核回复
    if crm.is_review_reply(email):
        # 解析指令
        instruction = crm.parse_instruction(email['body'])
        print(f"指令: {instruction}")
        
        # 处理指令
        crm.handle_instruction(instruction, email)
```

#### 启动监听服务

```bash
# 持续监听邮件回复
python3 scripts/content_review_mail.py --loop
```

## 邮件接收方式

### 方式1：IMAP/POP3（传统方式）

适用于：服务器网络 unrestricted

配置 `config/config.json` 中的 IMAP 部分，系统会定时检查新邮件。

### 方式2：ForwardEmail Webhook（推荐）

适用于：服务器限制 IMAP/POP3 端口（如当前环境）

**优势：**
- 使用 HTTPS (443端口)，绕过 IMAP 限制
- 实时接收，秒级延迟
- 免费额度充足

**快速设置：**

1. 访问 https://forwardemail.net 注册账号
2. 添加域名或使用子域名
3. 配置 Webhook URL：`http://你的服务器IP:8888/webhook`
4. 启动接收器：
   ```bash
   python3 scripts/forwardemail_webhook.py --port 8888
   ```

详细配置见 [FORWARDEMAIL_GUIDE.md](FORWARDEMAIL_GUIDE.md)

## 支持的指令

用户回复邮件时可以使用的指令：

### 1. 发布文章
```
发布 2
```
或
```
采用候选2
```

### 2. 重新生成
```
重新生成
方向：更侧重AI工具的具体操作步骤，少讲理论
```

### 3. 修改优化
```
修改 1

问题：
- 案例分析部分太笼统
- 缺少数据支撑
- 建议不够可执行
```

### 4. 跳过今日
```
跳过
```

### 5. 查看完整
```
查看 3
```

## 邮件模板

审核邮件包含：
- 候选文章列表（标题、角度、分数）
- 内容预览（前500字）
- 操作指南（回复指令示例）
- 截止时间提醒

## 工作流程

```
1. 生成内容 → 准备多候选
       ↓
2. 调用 send_review_email() 发送审核邮件
       ↓
3. 用户收到邮件，查看候选
       ↓
4. 用户回复邮件（如："发布 2"）
       ↓
5. 系统 check_new_emails() 检测到回复
       ↓
6. 系统 parse_instruction() 解析指令
       ↓
7. 系统 handle_instruction() 执行操作
       ↓
8. 系统 send_reply_email() 发送确认
       ↓
9. 如需讨论，循环步骤4-8
```

## API 参考

### ContentReviewMail 类

#### 初始化
```python
crm = ContentReviewMail(config_path='config/config.json')
```

#### 方法

**send_review_email(to, subject, candidates, article_date)**
- 发送审核邮件
- 参数：收件人、主题、候选列表、文章日期
- 返回：bool

**check_new_emails()**
- 检查新邮件
- 返回：邮件列表

**is_review_reply(email)**
- 判断是否是审核回复
- 参数：邮件字典
- 返回：bool

**parse_instruction(email_content)**
- 解析邮件中的指令
- 参数：邮件正文
- 返回：指令字典

**send_reply_email(to, subject, content)**
- 发送回复邮件
- 参数：收件人、主题、内容
- 返回：bool

**run_mail_loop()**
- 启动邮件监听循环
- 持续运行直到中断

## 状态管理

系统会维护以下状态文件：
- `state/mail_state.json` - 邮件状态、待审核列表、处理历史

## 故障排查

### 无法发送邮件
1. 检查 SMTP 配置
2. 确认授权码正确
3. 检查邮箱是否开启SMTP服务

### 无法读取邮件
1. 检查 IMAP 配置
2. 确认授权码有IMAP权限
3. 检查邮箱文件夹名称（INBOX）

### 指令解析失败
1. 检查邮件正文是否包含指令关键词
2. 查看日志中的解析结果
3. 使用更明确的指令格式

## 示例

见 `examples/` 目录：
- `send_review.py` - 发送审核邮件示例
- `handle_reply.py` - 处理回复示例
- `mail_loop.py` - 监听服务示例

## License

MIT
