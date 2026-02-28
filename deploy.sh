#!/bin/bash
# Deploy script for WeChat Content Management System
# Usage: ./deploy.sh [install|start|stop|status]

set -e

# Configuration
PROJECT_DIR="/root/.openclaw/workspace"
APP_DIR="$PROJECT_DIR/content-pipeline/article_library"
SERVICE_NAME="wechat-content"
PORT=8080

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Please run as root or with sudo"
    fi
}

# Install dependencies
install() {
    log "Installing dependencies..."
    
    # Check Python version
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    log "Python version: $python_version"
    
    # Install Python packages
    cd "$PROJECT_DIR"
    pip3 install -r requirements.txt
    
    # Create necessary directories
    mkdir -p "$APP_DIR/logs"
    mkdir -p "$APP_DIR/data"
    
    # Check environment variables
    if [ -z "$WECHAT_APP_ID" ] || [ -z "$WECHAT_APP_SECRET" ]; then
        warn "WECHAT_APP_ID or WECHAT_APP_SECRET not set!"
        warn "Please configure WeChat API credentials:"
        warn "  export WECHAT_APP_ID=your-app-id"
        warn "  export WECHAT_APP_SECRET=your-app-secret"
    fi
    
    log "Installation completed!"
    log "Next steps:"
    log "  1. Configure environment variables"
    log "  2. Run: ./deploy.sh start"
}

# Start the service
start() {
    log "Starting WeChat Content Management System..."
    
    cd "$APP_DIR"
    
    # Check if already running
    if pgrep -f "web_server.py" > /dev/null; then
        warn "Service is already running!"
        exit 0
    fi
    
    # Initialize database if not exists
    if [ ! -f "$APP_DIR/library.db" ]; then
        log "Initializing database..."
        python3 -c "from library import ArticleLibrary; lib = ArticleLibrary(); print('Database initialized')"
    fi
    
    # Start server
    log "Starting web server on port $PORT..."
    nohup python3 web_server.py > "$APP_DIR/logs/server.log" 2>&1 &
    
    sleep 2
    
    # Check if started successfully
    if pgrep -f "web_server.py" > /dev/null; then
        log "✅ Service started successfully!"
        log "📚 Article Library: http://$(hostname -I | awk '{print $1}'):$PORT/library"
        log "📊 Dashboard: http://$(hostname -I | awk '{print $1}'):$PORT/dashboard"
    else
        error "Failed to start service. Check logs: $APP_DIR/logs/server.log"
    fi
}

# Stop the service
stop() {
    log "Stopping WeChat Content Management System..."
    
    if pgrep -f "web_server.py" > /dev/null; then
        pkill -f "web_server.py"
        log "✅ Service stopped"
    else
        warn "Service is not running"
    fi
}

# Check service status
status() {
    if pgrep -f "web_server.py" > /dev/null; then
        log "✅ Service is running"
        log "PID: $(pgrep -f "web_server.py")"
        log "Port: $PORT"
        log "Logs: $APP_DIR/logs/server.log"
    else
        warn "❌ Service is not running"
    fi
}

# Setup systemd service
setup_systemd() {
    log "Setting up systemd service..."
    
    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=WeChat Content Management System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment=WECHAT_APP_ID=${WECHAT_APP_ID}
Environment=WECHAT_APP_SECRET=${WECHAT_APP_SECRET}
ExecStart=/usr/bin/python3 $APP_DIR/web_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    log "Systemd service created!"
    log "Commands:"
    log "  systemctl start $SERVICE_NAME"
    log "  systemctl stop $SERVICE_NAME"
    log "  systemctl status $SERVICE_NAME"
}

# Backup data
backup() {
    backup_dir="/tmp/backup-$(date +%Y%m%d-%H%M%S)"
    log "Creating backup at $backup_dir..."
    
    mkdir -p "$backup_dir"
    cp -r "$APP_DIR/library.db" "$backup_dir/" 2>/dev/null || true
    cp -r "$APP_DIR/user_preferences.db" "$backup_dir/" 2>/dev/null || true
    cp -r "$APP_DIR/articles" "$backup_dir/" 2>/dev/null || true
    cp -r "$PROJECT_DIR/memory" "$backup_dir/" 2>/dev/null || true
    
    tar czvf "$backup_dir.tar.gz" -C /tmp "$(basename $backup_dir)"
    rm -rf "$backup_dir"
    
    log "✅ Backup created: $backup_dir.tar.gz"
}

# Show help
help() {
    echo "WeChat Content Management System - Deployment Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install       Install dependencies and setup"
    echo "  start         Start the service"
    echo "  stop          Stop the service"
    echo "  restart       Restart the service"
    echo "  status        Check service status"
    echo "  systemd       Setup systemd service"
    echo "  backup        Backup all data"
    echo "  help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 install"
    echo "  $0 start"
    echo "  $0 status"
}

# Main
case "${1:-help}" in
    install)
        check_root
        install
        ;;
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
    systemd)
        check_root
        setup_systemd
        ;;
    backup)
        backup
        ;;
    help|--help|-h)
        help
        ;;
    *)
        error "Unknown command: $1. Use '$0 help' for usage."
        ;;
esac
