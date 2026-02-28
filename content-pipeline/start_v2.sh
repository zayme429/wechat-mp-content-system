#!/bin/bash
# 高级内容管理系统 v2.0 启动脚本

echo "🚀 启动高级内容管理系统 v2.0"
echo ""

BASE_DIR="/root/.openclaw/workspace/content-pipeline"

cd $BASE_DIR

# 检查依赖
echo "📦 检查依赖..."
pip install feedparser requests -q 2>/dev/null
echo "✅ 依赖检查完成"

# 初始化数据库
echo "🗄️ 初始化数据库..."
python3 -c "
from src.database.content_db import ContentDatabase
db = ContentDatabase()
print('✅ 数据库已初始化')
"

# 测试多候选生成
echo ""
echo "🧪 运行测试生成（生成3个候选）..."
python3 pipeline_v2.py --run

echo ""
echo "✅ 系统启动完成！"
echo ""
echo "📋 接下来的操作："
echo ""
echo "1. 查看生成的候选："
echo "   ls -la output/$(date +%Y%m%d)/"
echo ""
echo "2. 选择发布（例如选择候选2）："
echo "   python3 pipeline_v2.py --select $(date +%Y%m%d) --candidate 2"
echo ""
echo "3. 查看Web管理面板："
echo "   打开浏览器访问: http://服务器IP:18789/content-pipeline/web/"
echo ""
echo "4. 查看审核指南："
echo "   cat REVIEW_GUIDE_V2.md"
echo ""
echo "5. 设置定时任务（每天8点生成）："
echo "   crontab -e"
echo "   添加: 0 8 * * * cd $BASE_DIR && python3 pipeline_v2.py --run"
echo ""
