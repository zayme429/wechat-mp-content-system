#!/bin/bash
# Content Review Mail 启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📧 Content Review Mail"
echo "======================"
echo ""

# 检查配置
if [ ! -f config/config.json ]; then
    echo "❌ 配置文件不存在"
    echo "请复制 config.example.json 为 config.json 并填写邮箱信息"
    exit 1
fi

# 检查依赖
if [ ! -d ../imap-smtp-email ]; then
    echo "❌ 依赖 imap-smtp-email skill 未安装"
    echo "请先安装: npx clawhub install imap-smtp-email --dir skills"
    exit 1
fi

# 显示菜单
echo "请选择操作:"
echo "  1) 发送审核邮件"
echo "  2) 检查回复邮件"
echo "  3) 启动监听服务"
echo "  4) 测试配置"
echo ""
read -p "输入选项 (1-4): " choice

case $choice in
  1)
    read -p "收件人邮箱: " to
    read -p "文章日期 (YYYYMMDD): " date
    python3 scripts/content_review_mail.py --send --to "$to" --date "$date" --subject "📄 内容审核 - $date"
    ;;
  2)
    echo "检查回复邮件..."
    python3 scripts/content_review_mail.py --check
    ;;
  3)
    echo "启动监听服务 (按 Ctrl+C 停止)..."
    python3 scripts/content_review_mail.py --loop
    ;;
  4)
    echo "测试配置..."
    python3 -c "
import json
with open('config/config.json') as f:
    config = json.load(f)
print('✅ 配置加载成功')
print(f'IMAP: {config[\"imap\"][\"host\"]}:{config[\"imap\"][\"port\"]}')
print(f'SMTP: {config[\"smtp\"][\"host\"]}:{config[\"smtp\"][\"port\"]}')
print(f'用户: {config[\"imap\"][\"user\"]}')
"
    ;;
  *)
    echo "无效选项"
    exit 1
    ;;
esac
