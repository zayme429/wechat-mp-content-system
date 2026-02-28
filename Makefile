.PHONY: help install start stop restart status backup migrate clean

# 默认目标
help:
	@echo "微信公众号文章管理系统 - 常用命令"
	@echo ""
	@echo "安装与启动:"
	@echo "  make install      安装依赖并初始化"
	@echo "  make start        启动服务"
	@echo "  make stop         停止服务"
	@echo "  make restart      重启服务"
	@echo "  make status       查看服务状态"
	@echo ""
	@echo "Docker部署:"
	@echo "  make docker-build 构建Docker镜像"
	@echo "  make docker-up    启动Docker容器"
	@echo "  make docker-down  停止Docker容器"
	@echo ""
	@echo "数据管理:"
	@echo "  make backup       备份数据"
	@echo "  make restore      从备份恢复"
	@echo "  make migrate      导出到另一台服务器"
	@echo ""
	@echo "维护:"
	@echo "  make clean        清理临时文件"
	@echo "  make logs         查看日志"

# 安装
install:
	@echo "📦 安装依赖..."
	pip install -r requirements.txt
	@echo "🗄️  初始化数据库..."
	cd content-pipeline/article_library && python3 -c "from library import ArticleLibrary; ArticleLibrary()"
	@echo "✅ 安装完成!"
	@echo ""
	@echo "下一步:"
	@echo "  1. 配置环境变量: export WECHAT_APP_ID=xxx"
	@echo "  2. 启动服务: make start"

# 启动
start:
	@echo "🚀 启动服务..."
	cd content-pipeline/article_library && ./start_server.sh
	@echo "✅ 服务已启动"
	@echo "📚 访问: http://localhost:8080/library"

# 停止
stop:
	@echo "🛑 停止服务..."
	-pkill -f "web_server.py"
	@echo "✅ 服务已停止"

# 重启
restart: stop start

# 状态
status:
	@if pgrep -f "web_server.py" > /dev/null; then \
		echo "✅ 服务运行中"; \
		echo "PID: $$(pgrep -f "web_server.py")"; \
		echo "访问: http://localhost:8080/library"; \
	else \
		echo "❌ 服务未运行"; \
	fi

# Docker构建
docker-build:
	@echo "🐳 构建Docker镜像..."
	docker build -t wechat-content:latest .
	@echo "✅ 镜像构建完成"

# Docker启动
docker-up:
	@echo "🐳 启动Docker容器..."
	docker-compose up -d
	@echo "✅ 容器已启动"
	@echo "📚 访问: http://localhost:8080/library"

# Docker停止
docker-down:
	@echo "🐳 停止Docker容器..."
	docker-compose down
	@echo "✅ 容器已停止"

# 备份
backup:
	@echo "💾 备份数据..."
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d-%H%M%S); \
	tar czvf backups/backup-$$timestamp.tar.gz \
		content-pipeline/article_library/library.db \
		content-pipeline/article_library/user_preferences.db \
		content-pipeline/article_library/articles/ \
		memory/ 2>/dev/null || true
	@echo "✅ 备份完成: backups/backup-$$timestamp.tar.gz"

# 恢复
restore:
	@echo "📂 可用的备份文件:"
	@ls -la backups/*.tar.gz 2>/dev/null || echo "没有找到备份文件"
	@echo ""
	@echo "使用: tar xzvf backups/backup-xxx.tar.gz"

# 迁移到另一台服务器
migrate:
	@echo "🚚 准备迁移..."
	@echo "1. 打包项目..."
	@cd .. && tar czvf /tmp/wechat-content-export.tar.gz \
		$$(basename $$(pwd)) \
		--exclude='__pycache__' \
		--exclude='*.pyc' \
		--exclude='.git'
	@echo "✅ 导出文件: /tmp/wechat-content-export.tar.gz"
	@echo ""
	@echo "2. 传输到新服务器:"
	@echo "   scp /tmp/wechat-content-export.tar.gz user@new-server:/tmp/"
	@echo ""
	@echo "3. 在新服务器执行:"
	@echo "   cd /tmp && tar xzvf wechat-content-export.tar.gz"
	@echo "   cd wechat-content && make install && make start"

# 清理
clean:
	@echo "🧹 清理临时文件..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
	@echo "✅ 清理完成"

# 查看日志
logs:
	@tail -f content-pipeline/article_library/logs/*.log 2>/dev/null || \
	tail -f content-pipeline/logs/*.log 2>/dev/null || \
	echo "没有找到日志文件"
