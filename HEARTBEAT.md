# HEARTBEAT.md

## 定时任务

### 检查审核回复（每次心跳）
运行 `~/.openclaw/workspace/content-pipeline/check_replies_sendclaw.py`，检查 SendClaw 是否有新的审核回复邮件。如果有，解析回复内容并通知用户。
