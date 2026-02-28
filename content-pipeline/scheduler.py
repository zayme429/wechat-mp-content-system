#!/usr/bin/env python3
"""
定时调度管理
设置每日自动执行内容生成Pipeline
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

def setup_cron():
    """设置cron定时任务"""
    
    pipeline_path = '/root/.openclaw/workspace/content-pipeline/pipeline.py'
    log_path = '/root/.openclaw/workspace/content-pipeline/logs/cron.log'
    
    # 每天早上 8:00 执行内容生成
    cron_line = f"0 8 * * * /usr/bin/python3 {pipeline_path} >> {log_path} 2>&1"
    
    print("📅 建议的Cron配置：")
    print(f"  {cron_line}")
    print()
    print("添加到crontab的方法：")
    print("  1. 执行: crontab -e")
    print(f"  2. 添加上面这行")
    print("  3. 保存退出")
    print()
    
    # 检查是否已有crontab
    result = os.popen('crontab -l 2>/dev/null').read()
    if 'content-pipeline' in result:
        print("✅ 检测到已有定时任务")
    else:
        print("⚠️  尚未配置定时任务")
        
    return cron_line

def manual_run():
    """手动执行一次"""
    print("🚀 手动执行Pipeline...")
    
    pipeline_path = '/root/.openclaw/workspace/content-pipeline/pipeline.py'
    
    import subprocess
    result = subprocess.run(
        ['/usr/bin/python3', pipeline_path],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("错误输出:", result.stderr)
    
    print(f"返回码: {result.returncode}")

def check_status():
    """检查Pipeline状态"""
    
    memory_path = '/root/.openclaw/workspace/content-pipeline/memory/published.json'
    log_path = '/root/.openclaw/workspace/content-pipeline/logs/pipeline.log'
    
    print("=== 📊 Pipeline 状态检查 ===\n")
    
    # 检查历史发布
    if os.path.exists(memory_path):
        with open(memory_path, 'r') as f:
            memory = json.load(f)
        articles = memory.get('articles', [])
        print(f"📚 已生成文章: {len(articles)} 篇")
        if articles:
            latest = articles[-1]
            print(f"   最新: {latest.get('date', 'N/A')[:10]} - {latest.get('topic', 'N/A')[:30]}...")
    else:
        print("📚 暂无历史记录")
    
    # 检查日志
    if os.path.exists(log_path):
        size = os.path.getsize(log_path)
        print(f"📝 日志文件: {size} bytes")
        
        # 显示最后几行
        print("\n最近日志:")
        with open(log_path, 'r') as f:
            lines = f.readlines()
            for line in lines[-10:]:
                print(f"  {line.rstrip()}")
    else:
        print("📝 暂无日志文件")
    
    print("\n=== ✅ 状态检查完成 ===")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python scheduler.py <command>")
        print()
        print("可用命令:")
        print("  setup     - 显示Cron配置建议")
        print("  run       - 手动执行一次Pipeline")
        print("  status    - 检查Pipeline状态")
        print()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'setup':
        setup_cron()
    elif command == 'run':
        manual_run()
    elif command == 'status':
        check_status()
    else:
        print(f"未知命令: {command}")
        sys.exit(1)
