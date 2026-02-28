# ForwardEmail 配置指南

## 🎯 概述

由于服务器网络限制无法使用 IMAP/POP3，我们使用 **ForwardEmail** 通过 HTTPS Webhook 接收邮件回复。

**优势：**
- ✅ 绕过 IMAP 端口限制
- ✅ 实时接收邮件（秒级延迟）
- ✅ 免费额度足够个人使用
- ✅ 稳定可靠，无需维护

---

## 🚀 快速设置（5分钟）

### 步骤1：注册 ForwardEmail

1. 访问 https://forwardemail.net
2. 点击 "Sign Up" 注册账号
3. 选择免费套餐（Free Plan）
4. 验证邮箱

### 步骤2：配置域名

**方式A：使用自己的域名（推荐）**

1. 在 ForwardEmail 控制台点击 "Add Domain"
2. 输入你的域名（如：yourdomain.com）
3. 按照提示添加 DNS 记录（MX记录和TXT记录）
4. 等待 DNS 生效（通常几分钟到几小时）

**方式B：使用 ForwardEmail 的子域名**

1. 在控制台点击 "Create Alias"
2. 选择一个可用的子域名（如：yourname.forwardemail.net）
3. 创建邮箱地址：review@yourname.forwardemail.net

### 步骤3：配置 Webhook

1. 在 ForwardEmail 控制台找到你的域名/别名
2. 点击 "Webhooks" 或 "Advanced Settings"
3. 添加 Webhook URL：
   ```
   http://154.9.252.35:8888/webhook
   ```
   或如果你有域名：
   ```
   https://your-domain.com/webhook
   ```

4. 选择触发条件：
   - ✅ "All Emails" - 接收所有邮件
   - 或 "Specific Recipients" - 只接收特定收件人的邮件

5. 保存配置

### 步骤4：启动 Webhook 接收器

在你的服务器上运行：

```bash
cd /root/.openclaw/workspace/skills/content-review-mail
python3 scripts/forwardemail_webhook.py --port 8888
```

或使用 nohup 后台运行：
```bash
nohup python3 scripts/forwardemail_webhook.py --port 8888 > logs/webhook.log 2>&1 &
```

### 步骤5：测试

1. 发送测试邮件到配置的地址：
   ```
   收件人：review@your-domain.com
   主题：Re: 内容审核 - 20260226
   内容：发布 1
   ```

2. 检查 Webhook 日志，确认收到转发

3. 确认系统执行了指令并发送了回复邮件

---

## 📋 Webhook 数据格式

ForwardEmail 发送的 JSON 数据示例：

```json
{
  "from": "user@example.com",
  "to": "review@your-domain.com",
  "subject": "Re: 内容审核 - 20260226",
  "text": "发布 1",
  "html": "<p>发布 1</p>",
  "attachments": [],
  "headers": {...}
}
```

---

## 🔧 高级配置

### 使用 HTTPS（生产环境）

如果使用域名并配置 HTTPS：

```bash
# 使用 Nginx 反向代理
# nginx.conf
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location /webhook {
        proxy_pass http://localhost:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 多域名配置

可以同时配置多个域名接收邮件：

```python
# 修改 forwardemail_webhook.py
ALLOWED_DOMAINS = [
    'review.yourdomain.com',
    'content.yourdomain.com'
]
```

### 邮件过滤

只处理特定主题的邮件：

```python
# 在 _process_email 方法中添加过滤
if '内容审核' not in subject:
    logger.info("跳过非审核邮件")
    return
```

---

## 🐛 故障排查

### 问题1：Webhook 无法访问

**症状：** ForwardEmail 显示 webhook 请求失败

**解决：**
```bash
# 检查端口是否开放
sudo ufw allow 8888

# 或检查防火墙
sudo iptables -L -n | grep 8888
```

### 问题2：收不到邮件转发

**症状：** 发送邮件后 webhook 没有触发

**检查：**
1. DNS 记录是否正确配置
2. 域名验证是否完成
3. Webhook URL 是否可访问
4. ForwardEmail 控制台是否有错误日志

### 问题3：邮件内容乱码

**症状：** 中文显示为乱码

**解决：**
```python
# 在 handler 中添加编码处理
data = json.loads(post_data.decode('utf-8'))
```

---

## 💰 费用说明

**ForwardEmail 免费套餐：**
- 每月 10,000 封邮件转发
- 5 个域名
- 无限邮箱别名
- 基础 Webhook 功能

**对于内容审核系统完全足够！**

---

## 🔗 相关链接

- ForwardEmail 官网：https://forwardemail.net
- 文档：https://forwardemail.net/docs
- GitHub：https://github.com/forwardemail

---

## 📞 支持

配置过程中遇到问题：
1. 查看 ForwardEmail 官方文档
2. 检查服务器日志：`tail -f logs/webhook.log`
3. 联系 ForwardEmail 支持团队
