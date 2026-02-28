#!/bin/bash
# Content Pipeline v2.0 定时任务
# 每天早上8点生成内容并发送审核邮件

# 设置环境变量
export WECHAT_APP_ID=wx5c6f2e9b5734ddd5
export WECHAT_APP_SECRET=baf071b9ca8e805992a26111c552b9f9
export PATH="/usr/local/bin:/usr/bin:$PATH"

# 日志文件
LOG_FILE="/root/.openclaw/workspace/content-pipeline/logs/cron.log"
DATE=$(date +%Y-%m-%d_%H:%M:%S)

echo "[$DATE] ====== Content Pipeline v2.0 启动 ======" >> $LOG_FILE

# 进入项目目录
cd /root/.openclaw/workspace/content-pipeline

# 运行多候选生成流程（发送审核邮件）
/usr/bin/python3 pipeline_v2.py --run >> $LOG_FILE 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$DATE] ✅ Pipeline 执行成功，审核邮件已发送" >> $LOG_FILE
else
    echo "[$DATE] ❌ Pipeline 执行失败 (exit code: $EXIT_CODE)" >> $LOG_FILE
fi

echo "[$DATE] ====== Pipeline 执行结束 ======" >> $LOG_FILE
echo "" >> $LOG_FILE
