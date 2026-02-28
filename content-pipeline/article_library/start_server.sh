#!/bin/bash
# 启动文章管理库 Web 服务

WORKSPACE="/root/.openclaw/workspace/content-pipeline"
PIDFILE="/tmp/article_library.pid"

start() {
    echo "🚀 启动文章管理库 Web 服务..."
    cd "$WORKSPACE"
    
    # 检查是否已在运行
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️ 服务已在运行 (PID: $PID)"
            echo "访问地址: http://154.9.252.35:8080/library"
            return 0
        fi
    fi
    
    # 启动服务（后台运行）
    nohup python3 article_library/web_server.py > /tmp/article_library.log 2>&1 &
    echo $! > "$PIDFILE"
    
    sleep 2
    
    if ps -p $(cat "$PIDFILE") > /dev/null 2>&1; then
        echo "✅ 服务启动成功"
        echo "📚 文章库访问地址: http://154.9.252.35:8080/library"
        echo ""
        echo "📋 管理命令:"
        echo "   查看日志: tail -f /tmp/article_library.log"
        echo "   停止服务: kill $(cat $PIDFILE)"
    else
        echo "❌ 启动失败，查看日志: /tmp/article_library.log"
        return 1
    fi
}

stop() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "🛑 停止服务 (PID: $PID)..."
            kill "$PID"
            rm -f "$PIDFILE"
            echo "✅ 服务已停止"
        else
            echo "⚠️ 服务未在运行"
            rm -f "$PIDFILE"
        fi
    else
        echo "⚠️ 服务未在运行"
    fi
}

status() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ 服务运行中 (PID: $PID)"
            echo "📚 访问地址: http://154.9.252.35:8080/library"
        else
            echo "❌ 服务未运行（PID文件存在但进程不存在）"
        fi
    else
        echo "❌ 服务未运行"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
