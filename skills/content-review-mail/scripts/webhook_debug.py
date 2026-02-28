#!/usr/bin/env python3
"""
ForwardEmail/Zapier Webhook 接收器 - 修复版
详细记录原始数据，确保正确解析
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

# 详细日志
logging.basicConfig(
    level=logging.DEBUG,  # 改为 DEBUG 级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/.openclaw/workspace/skills/content-review-mail/logs/webhook_detailed.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WebhookHandler(BaseHTTPRequestHandler):
    """处理 Webhook 请求"""
    
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
            # 记录请求头
            logger.debug(f"请求头: {dict(self.headers)}")
            
            # 获取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            logger.debug(f"Content-Length: {content_length}")
            
            if content_length == 0:
                logger.warning("收到空请求体")
                self._send_error(400, 'Empty request body')
                return
            
            post_data = self.rfile.read(content_length)
            raw_data = post_data.decode('utf-8', errors='replace')
            
            # 记录原始数据（关键！）
            logger.info(f"=== 原始数据 ===")
            logger.info(raw_data[:1000])  # 记录前1000字符
            logger.info(f"=== 原始数据结束 ===")
            
            # 尝试解析数据
            data = self._parse_data(raw_data)
            
            if not data:
                logger.error("无法解析数据")
                self._send_error(400, 'Cannot parse data')
                return
            
            # 记录解析后的数据
            logger.info(f"解析后的数据: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
            
            # 处理邮件
            self._process_email(data)
            
            # 返回成功
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'ok',
                'message': 'Email processed successfully'
            }).encode())
            
        except Exception as e:
            logger.error(f"处理 Webhook 失败: {e}", exc_info=True)
            self._send_error(500, str(e))
    
    def _parse_data(self, raw_data: str) -> dict:
        """解析各种格式的数据"""
        data = {}
        
        # 尝试1: JSON 格式
        try:
            data = json.loads(raw_data)
            logger.info("✅ 成功解析为 JSON")
            return data
        except json.JSONDecodeError:
            logger.debug("不是 JSON 格式")
        
        # 尝试2: Form 格式 (URL-encoded)
        try:
            from urllib.parse import parse_qs
            parsed = parse_qs(raw_data)
            if parsed:
                data = {k: v[0] if v else '' for k, v in parsed.items()}
                logger.info(f"✅ 成功解析为 Form 格式: {list(data.keys())}")
                return data
        except Exception as e:
            logger.debug(f"Form 解析失败: {e}")
        
        # 尝试3: 简单文本
        data['raw_body'] = raw_data
        logger.info("⚠️ 使用原始文本")
        return data
    
    def _process_email(self, data: dict):
        """处理接收到的邮件"""
        # 尝试多种可能的字段名
        from_addr = (data.get('from') or 
                    data.get('From') or 
                    data.get('from_email') or 
                    data.get('sender') or 
                    'unknown')
        
        subject = (data.get('subject') or 
                  data.get('Subject') or 
                  data.get('title') or 
                  '')
        
        # 尝试多种 body 字段
        body = (data.get('body') or 
               data.get('Body') or 
               data.get('text') or 
               data.get('Text') or 
               data.get('html') or 
               data.get('Html') or 
               data.get('message') or 
               data.get('raw_body') or 
               '')
        
        logger.info(f"提取的字段:")
        logger.info(f"  from: {from_addr}")
        logger.info(f"  subject: {subject}")
        logger.info(f"  body: {body[:200]}...")  # 只显示前200字符
        
        # 初始化处理
        crm = ContentReviewMail()
        
        # 检查是否是审核回复
        email_info = {'subject': subject, 'from': from_addr, 'body': body}
        if crm.is_review_reply(email_info):
            logger.info("✅ 这是审核回复邮件")
            instruction = crm.parse_instruction(body)
            logger.info(f"🎯 解析到指令: {instruction}")
            # 这里可以添加执行逻辑
        else:
            logger.info("❌ 这不是审核回复")
    
    def _send_error(self, code: int, message: str):
        """发送错误响应"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'error',
            'message': message
        }).encode())
    
    def log_message(self, format, *args):
        """自定义日志"""
        logger.info(format % args)

def main():
    """主函数"""
    server = HTTPServer(('0.0.0.0', 8888), WebhookHandler)
    logger.info("🚀 Webhook 服务启动 (调试模式)")
    logger.info("监听地址: http://0.0.0.0:8888")
    logger.info("详细日志: logs/webhook_detailed.log")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("服务已停止")
        server.shutdown()

if __name__ == '__main__':
    main()
