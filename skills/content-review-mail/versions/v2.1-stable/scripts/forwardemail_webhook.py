#!/usr/bin/env python3
"""
ForwardEmail Webhook 接收器
通过 HTTPS 接收邮件，绕过 IMAP 限制
"""

import json
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread
import sys

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from content_review_mail import ContentReviewMail

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ForwardEmailHandler(BaseHTTPRequestHandler):
    """处理 ForwardEmail Webhook"""
    
    def do_GET(self):
        """处理 GET 请求（用于测试）"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'message': 'Webhook is running',
            'timestamp': datetime.now().isoformat()
        }).encode())
    
    def do_POST(self):
        """处理 POST 请求"""
        try:
            # 获取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length == 0:
                logger.warning("收到空请求体")
                self._send_error(400, 'Empty request body')
                return
            
            post_data = self.rfile.read(content_length)
            
            # 尝试解析 JSON
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                logger.debug(f"原始数据: {post_data[:200]}")
                # 尝试解析 form 数据
                data = self._parse_form_data(post_data.decode('utf-8'))
            
            logger.info("📧 收到 Webhook 请求")
            logger.info(f"发件人: {data.get('from')}")
            logger.info(f"主题: {data.get('subject')}")
            
            # 处理邮件
            self._process_email(data)
            
            # 返回成功响应
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'ok',
                'message': 'Email processed successfully'
            }).encode())
            
        except Exception as e:
            logger.error(f"处理 Webhook 失败: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _parse_form_data(self, data_str: str) -> dict:
        """解析 form 格式数据"""
        result = {}
        try:
            # 尝试解析 URL-encoded 格式
            from urllib.parse import parse_qs
            parsed = parse_qs(data_str)
            for key, values in parsed.items():
                result[key] = values[0] if values else ''
        except Exception as e:
            logger.error(f"Form解析失败: {e}")
        return result
    
    def _send_error(self, code: int, message: str):
        """发送错误响应"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'error',
            'message': message
        }).encode())
    
    def _process_email(self, data: dict):
        """处理接收到的邮件"""
        from_addr = data.get('from', '')
        subject = data.get('subject', '')
        body = data.get('body', '') or data.get('text', '') or data.get('html', '') or data.get('Body', '')
        
        # 初始化 ContentReviewMail
        crm = ContentReviewMail()
        
        # 检查是否是审核回复
        if crm.is_review_reply({'subject': subject, 'from': from_addr}):
            logger.info("✅ 这是审核回复邮件")
            
            # 解析指令
            instruction = crm.parse_instruction(body)
            logger.info(f"🎯 解析到指令: {instruction}")
            
            # 执行指令
            self._execute_instruction(instruction, from_addr, subject)
        else:
            logger.info("❌ 这不是审核回复")
    
    def _execute_instruction(self, instruction: dict, reply_to: str, original_subject: str):
        """执行指令并回复"""
        action = instruction.get('action')
        
        crm = ContentReviewMail()
        
        if action == 'publish':
            candidate = instruction.get('candidate', 1)
            # 发布逻辑
            logger.info(f"🚀 执行发布候选 {candidate}")
            # 这里调用发布功能
            
            # 发送确认回复
            crm.send_reply_email(
                to=reply_to,
                subject=f"Re: {original_subject}",
                content=f"✅ 已收到您的指令：发布候选 {candidate}\n\n正在处理中，请稍候..."
            )
            
        elif action == 'regenerate':
            direction = instruction.get('direction', '')
            logger.info(f"🔄 执行重新生成，方向: {direction}")
            
            crm.send_reply_email(
                to=reply_to,
                subject=f"Re: {original_subject}",
                content=f"✅ 已收到重新生成请求\n方向: {direction}\n\n正在生成新的候选文章..."
            )
            
        elif action == 'modify':
            candidate = instruction.get('candidate', 1)
            feedback = instruction.get('feedback', '')
            logger.info(f"✏️ 执行修改候选 {candidate}")
            
            crm.send_reply_email(
                to=reply_to,
                subject=f"Re: {original_subject}",
                content=f"✅ 已收到修改意见\n候选: {candidate}\n意见: {feedback}\n\n正在优化..."
            )
            
        elif action == 'skip':
            logger.info("⏭️ 执行跳过")
            
            crm.send_reply_email(
                to=reply_to,
                subject=f"Re: {original_subject}",
                content="✅ 已收到跳过指令\n\n今日不发布，明天继续生成新内容。"
            )
            
        else:
            logger.warning(f"⚠️ 未知指令: {action}")
    
    def log_message(self, format, *args):
        """自定义日志"""
        logger.info(format % args)

class ForwardEmailWebhook:
    """ForwardEmail Webhook 服务"""
    
    def __init__(self, host='0.0.0.0', port=8888):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
    
    def start(self):
        """启动 Webhook 服务"""
        self.server = HTTPServer((self.host, self.port), ForwardEmailHandler)
        logger.info(f"🚀 ForwardEmail Webhook 服务启动")
        logger.info(f"监听地址: http://{self.host}:{self.port}")
        logger.info(f"Webhook URL: http://154.9.252.35:{self.port}/webhook")
        
        # 在后台线程运行
        self.thread = Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("✅ Webhook 服务已启动（后台运行）")
    
    def stop(self):
        """停止服务"""
        if self.server:
            self.server.shutdown()
            logger.info("✅ Webhook 服务已停止")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ForwardEmail Webhook 服务')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8888, help='监听端口')
    
    args = parser.parse_args()
    
    webhook = ForwardEmailWebhook(host=args.host, port=args.port)
    webhook.start()
    
    print("\n按 Ctrl+C 停止服务\n")
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        webhook.stop()

if __name__ == '__main__':
    main()

# 添加调试日志
import logging
logging.basicConfig(level=logging.DEBUG)
