#!/usr/bin/env python3
"""
Content Review Mail - 内容审核邮件系统
通过邮件实现内容审核的双向通信
"""

import os
import sys
import json
import re
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import subprocess

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContentReviewMail:
    """内容审核邮件系统"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'config.json'
        
        self.config = self._load_config(config_path)
        self.base_dir = Path(__file__).parent.parent
        self.state_file = self.base_dir / 'state' / 'mail_state.json'
        self.state_file.parent.mkdir(exist_ok=True)
        
        self._load_state()
    
    def _load_config(self, config_path: Path) -> Dict:
        """加载配置"""
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'imap': {
                'host': 'imap.gmail.com',
                'port': 993,
                'user': '',
                'pass': '',
                'tls': True,
                'mailbox': 'INBOX'
            },
            'smtp': {
                'host': 'smtp.gmail.com',
                'port': 587,
                'secure': False,
                'user': '',
                'pass': '',
                'from': ''
            },
            'review': {
                'check_interval_minutes': 5,
                'auto_reply': True,
                'save_history': True
            }
        }
    
    def _load_state(self):
        """加载状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)
        else:
            self.state = {
                'last_check_time': None,
                'pending_reviews': {},
                'processed_emails': [],
                'conversation_history': []
            }
    
    def _save_state(self):
        """保存状态"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def check_new_emails(self) -> List[Dict]:
        """检查新邮件 - 使用 Python imaplib"""
        logger.info("检查新邮件...")
        
        try:
            import imaplib
            import email
            from datetime import datetime, timedelta
            
            # 连接 IMAP 服务器
            imap_config = self.config['imap']
            
            if imap_config.get('tls', True):
                server = imaplib.IMAP4_SSL(imap_config['host'], imap_config['port'])
            else:
                server = imaplib.IMAP4(imap_config['host'], imap_config['port'])
            
            # 登录
            server.login(imap_config['user'], imap_config['pass'])
            
            # 选择邮箱
            server.select(imap_config.get('mailbox', 'INBOX'))
            
            # 搜索未读邮件
            status, messages = server.search(None, 'UNSEEN')
            
            emails = []
            if status == 'OK' and messages[0]:
                msg_ids = messages[0].split()
                logger.info(f"找到 {len(msg_ids)} 封未读邮件")
                
                for msg_id in msg_ids[-10:]:  # 只取最近10封
                    status, msg_data = server.fetch(msg_id, '(RFC822)')
                    if status == 'OK':
                        raw_email = msg_data[0][1]
                        email_message = email.message_from_bytes(raw_email)
                        
                        # 提取邮件信息
                        subject = self._decode_header(email_message['Subject'])
                        from_addr = self._decode_header(email_message['From'])
                        date = email_message['Date']
                        
                        # 提取正文
                        body = self._get_email_body(email_message)
                        
                        emails.append({
                            'id': msg_id.decode(),
                            'subject': subject,
                            'from': from_addr,
                            'date': date,
                            'body': body
                        })
            
            server.close()
            server.logout()
            
            logger.info(f"成功获取 {len(emails)} 封邮件")
            return emails
            
        except Exception as e:
            logger.error(f"检查邮件异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _decode_header(self, header):
        """解码邮件头"""
        if not header:
            return ''
        try:
            decoded = email.header.decode_header(header)
            result = []
            for part, charset in decoded:
                if isinstance(part, bytes):
                    result.append(part.decode(charset or 'utf-8', errors='replace'))
                else:
                    result.append(part)
            return ''.join(result)
        except:
            return str(header)
    
    def _get_email_body(self, email_message):
        """获取邮件正文"""
        body = ''
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        break
                    except:
                        pass
                elif content_type == 'text/html' and not body:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    except:
                        pass
        else:
            try:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='replace')
            except:
                body = str(email_message.get_payload())
        return body
    
    def _parse_imap_output(self, output: str) -> List[Dict]:
        """解析 IMAP 输出"""
        emails = []
        # 这里需要根据实际输出格式解析
        # 假设输出是 JSON 格式
        try:
            data = json.loads(output)
            emails = data.get('emails', [])
        except:
            # 如果不是 JSON，尝试行解析
            lines = output.strip().split('\n')
            for line in lines:
                if line.startswith('UID:'):
                    parts = line.split('|')
                    email = {}
                    for part in parts:
                        if ':' in part:
                            key, value = part.split(':', 1)
                            email[key.strip()] = value.strip()
                    if email:
                        emails.append(email)
        
        return emails
    
    def is_review_reply(self, email: Dict) -> bool:
        """判断是否是审核回复邮件"""
        subject = email.get('subject', '')
        from_addr = email.get('from', '')
        
        # 检查主题是否包含审核相关关键词
        keywords = ['审核', '回复', 'Re:', '候选', '文章', '发布', 'review', 'candidate', '测试', 'test']
        if any(kw in subject for kw in keywords):
            return True
        
        # 如果发件人是用户，也认为是审核回复（宽松模式）
        if 'zayme' in from_addr.lower() or 'shaw' in from_addr.lower():
            return True
        
        return False
    
    def parse_instruction(self, email_content: str) -> Dict:
        """解析邮件中的指令"""
        content = email_content.lower()
        
        instruction = {
            'action': None,
            'candidate': None,
            'direction': None,
            'feedback': None
        }
        
        # 首先提取所有反馈内容（在解析指令前）
        # 提取数字列表项（如 1. xxx 2. xxx）
        feedback_items = []
        for line in email_content.split('\n'):
            line = line.strip()
            # 匹配数字开头的行（如 "1. 不要强行讲故事"）
            if re.match(r'^\d+[.、]\s*', line):
                feedback_items.append(line)
            # 匹配具体建议
            elif any(kw in line for kw in ['比如', '例如', '建议', '意见', '避免', '不要']):
                feedback_items.append(line)
        
        if feedback_items:
            instruction['feedback'] = '\n'.join(feedback_items)
        
        # 解析发布指令
        if any(kw in content for kw in ['发布', 'publish', '确认', 'ok', '采用']):
            instruction['action'] = 'publish'
            # 提取候选编号
            match = re.search(r'候选\s*(\d+)|candidate\s*(\d+)|(\d+)号', content)
            if match:
                instruction['candidate'] = int(match.group(1) or match.group(2) or match.group(3))
            # 如果没有明确数字，但有反馈内容，默认候选1
            elif instruction.get('feedback'):
                instruction['candidate'] = 1
        
        # 解析重新生成指令
        elif any(kw in content for kw in ['重新生成', 'regenerate', '重写', '再来']):
            instruction['action'] = 'regenerate'
            # 提取方向
            if '方向' in email_content or '侧重' in email_content:
                # 提取方向描述
                lines = email_content.split('\n')
                for line in lines:
                    if any(kw in line for kw in ['方向', '侧重', '重点']):
                        instruction['direction'] = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                        break
        
        # 解析修改指令
        elif any(kw in content for kw in ['修改', 'modify', '优化', '调整']):
            instruction['action'] = 'modify'
            match = re.search(r'候选\s*(\d+)|candidate\s*(\d+)|(\d+)号', content)
            if match:
                instruction['candidate'] = int(match.group(1) or match.group(2) or match.group(3))
            # 提取修改意见
            lines = email_content.split('\n')
            feedback_lines = []
            for line in lines:
                if any(kw in line for kw in ['问题', '建议', '意见', '需要', '应该']):
                    feedback_lines.append(line)
            instruction['feedback'] = '\n'.join(feedback_lines)
        
        # 解析跳过指令
        elif any(kw in content for kw in ['跳过', 'skip', '今天不发', '取消']):
            instruction['action'] = 'skip'
        
        # 解析查看指令
        elif any(kw in content for kw in ['查看', 'view', '看看', '全文']):
            instruction['action'] = 'view'
            match = re.search(r'候选\s*(\d+)|candidate\s*(\d+)|(\d+)号', content)
            if match:
                instruction['candidate'] = int(match.group(1) or match.group(2) or match.group(3))
        
        return instruction
    
    def send_review_email(self, to: str, subject: str, candidates: List[Dict], 
                         article_date: str) -> bool:
        """发送审核邮件"""
        logger.info(f"发送审核邮件到: {to}")
        
        # 构建邮件内容
        html_content = self._build_review_html(candidates, article_date)
        
        try:
            # 直接使用 Python smtplib 发送
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config['smtp']['from']
            msg['To'] = to
            
            # 添加 HTML 内容
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 连接 SMTP 服务器
            smtp_config = self.config['smtp']
            
            if smtp_config['secure']:
                # SSL 连接 (端口 465)
                server = smtplib.SMTP_SSL(smtp_config['host'], smtp_config['port'])
            else:
                # STARTTLS 连接 (端口 587)
                server = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
                server.starttls()
            
            # 登录
            server.login(smtp_config['user'], smtp_config['pass'])
            
            # 发送邮件
            server.sendmail(smtp_config['from'], to, msg.as_string())
            server.quit()
            
            logger.info("✅ 审核邮件已发送")
            
            # 保存到待审核列表
            self.state['pending_reviews'][article_date] = {
                'date': article_date,
                'candidates': candidates,
                'sent_time': datetime.now().isoformat(),
                'status': 'waiting_reply'
            }
            self._save_state()
            
            return True
                
        except Exception as e:
            logger.error(f"发送邮件异常: {e}")
            return False
    
    def _build_review_html(self, candidates: List[Dict], article_date: str) -> str:
        """构建审核邮件 HTML"""
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .candidate {{ background: #f8f9fa; border-left: 4px solid #667eea; 
                     padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
        .candidate h2 {{ margin-top: 0; color: #667eea; font-size: 18px; }}
        .meta {{ display: flex; gap: 15px; margin: 10px 0; font-size: 14px; color: #666; }}
        .meta span {{ background: #e9ecef; padding: 4px 12px; border-radius: 20px; }}
        .preview {{ background: white; padding: 15px; border-radius: 8px; 
                   margin: 15px 0; border: 1px solid #dee2e6; max-height: 300px; overflow-y: auto; }}
        .actions {{ margin: 20px 0; padding: 20px; background: #e7f3ff; border-radius: 8px; }}
        .actions h3 {{ margin-top: 0; color: #0066cc; }}
        .action-list {{ line-height: 2; }}
        .action-list code {{ background: #f4f4f4; padding: 2px 8px; border-radius: 4px; font-family: monospace; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📄 内容审核通知</h1>
        <p>{article_date} 已生成 {len(candidates)} 个候选文章，请审核</p>
    </div>
"""
        
        for i, c in enumerate(candidates, 1):
            preview = c.get('content', '')[:500] + '...' if len(c.get('content', '')) > 500 else c.get('content', '')
            
            html += f"""
    <div class="candidate">
        <h2>候选 {i}: {c.get('topic', f'候选{i}')}</h2>
        <div class="meta">
            <span>角度: {c.get('angle_type', '标准')}</span>
            <span>质量分: {c.get('quality_score', 0):.1f}</span>
            <span>独特分: {c.get('uniqueness_score', 0):.1f}</span>
            <span>字数: {c.get('word_count', 0)}</span>
        </div>
        <div class="preview">
            <strong>预览:</strong><br>
            {preview.replace(chr(10), '<br>')}
        </div>
    </div>
"""
        
        html += f"""
    <div class="actions">
        <h3>🎯 审核操作指南</h3>
        <div class="action-list">
            <p><strong>选择发布:</strong> 回复 <code>发布 [候选编号]</code> (如: 发布 2)</p>
            <p><strong>重新生成:</strong> 回复 <code>重新生成 [方向描述]</code> (如: 重新生成 更侧重实操)</p>
            <p><strong>修改优化:</strong> 回复 <code>修改 [候选编号] [具体要求]</code></p>
            <p><strong>跳过今日:</strong> 回复 <code>跳过</code></p>
            <p><strong>查看完整:</strong> 回复 <code>查看 [候选编号]</code></p>
        </div>
        <p><strong>截止时间:</strong> 24小时内未回复将自动选择最高分候选</p>
    </div>
</body>
</html>"""
        
        return html
    
    def send_reply_email(self, to: str, subject: str, content: str) -> bool:
        """发送回复邮件"""
        logger.info(f"发送回复邮件: {subject}")
        
        smtp_skill_path = Path.home() / '.openclaw' / 'workspace' / 'skills' / 'imap-smtp-email'
        
        try:
            env = os.environ.copy()
            env.update({
                'SMTP_HOST': self.config['smtp']['host'],
                'SMTP_PORT': str(self.config['smtp']['port']),
                'SMTP_SECURE': str(self.config['smtp']['secure']).lower(),
                'SMTP_USER': self.config['smtp']['user'],
                'SMTP_PASS': self.config['smtp']['pass'],
                'SMTP_FROM': self.config['smtp']['from']
            })
            
            # 创建临时文本文件
            temp_txt = self.base_dir / 'temp' / 'reply.txt'
            temp_txt.parent.mkdir(exist_ok=True)
            with open(temp_txt, 'w', encoding='utf-8') as f:
                f.write(content)
            
            result = subprocess.run(
                ['node', 'scripts/smtp.js', 'send',
                 '--to', to,
                 '--subject', subject,
                 '--text', str(temp_txt)],
                cwd=smtp_skill_path,
                capture_output=True,
                text=True,
                env=env,
                timeout=60
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"发送回复邮件失败: {e}")
            return False
    
    def run_mail_loop(self):
        """运行邮件监听循环"""
        logger.info("启动邮件监听服务...")
        
        while True:
            try:
                # 检查新邮件
                emails = self.check_new_emails()
                
                for email in emails:
                    # 检查是否是回复
                    if self.is_review_reply(email):
                        logger.info(f"收到审核回复: {email.get('subject', '')}")
                        
                        # 解析指令
                        instruction = self.parse_instruction(email.get('body', ''))
                        
                        # 处理指令
                        self.handle_instruction(instruction, email)
                
                # 更新检查时间
                self.state['last_check_time'] = datetime.now().isoformat()
                self._save_state()
                
                # 等待下一次检查
                interval = self.config.get('review', {}).get('check_interval_minutes', 5)
                logger.info(f"等待 {interval} 分钟后再次检查...")
                time.sleep(interval * 60)
                
            except KeyboardInterrupt:
                logger.info("邮件服务已停止")
                break
            except Exception as e:
                logger.error(f"邮件循环异常: {e}")
                time.sleep(60)
    
    def handle_instruction(self, instruction: Dict, email: Dict):
        """处理指令"""
        action = instruction.get('action')
        
        if action == 'publish':
            logger.info(f"执行发布操作，候选: {instruction.get('candidate')}")
            # 这里调用发布逻辑
            
        elif action == 'regenerate':
            logger.info(f"执行重新生成，方向: {instruction.get('direction')}")
            # 这里调用重新生成逻辑
            
        elif action == 'modify':
            logger.info(f"执行修改操作，候选: {instruction.get('candidate')}")
            # 这里调用修改逻辑
            
        elif action == 'skip':
            logger.info("执行跳过操作")
            
        elif action == 'view':
            logger.info(f"执行查看操作，候选: {instruction.get('candidate')}")
            # 发送完整内容

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Content Review Mail')
    parser.add_argument('--send', action='store_true', help='发送审核邮件')
    parser.add_argument('--check', action='store_true', help='检查回复邮件')
    parser.add_argument('--loop', action='store_true', help='启动监听循环')
    parser.add_argument('--to', type=str, help='收件人邮箱')
    parser.add_argument('--subject', type=str, help='邮件主题')
    parser.add_argument('--date', type=str, help='文章日期')
    
    args = parser.parse_args()
    
    crm = ContentReviewMail()
    
    if args.send:
        # 发送审核邮件
        candidates = []  # 这里需要传入实际候选
        crm.send_review_email(args.to, args.subject, candidates, args.date)
        
    elif args.check:
        # 检查回复
        emails = crm.check_new_emails()
        for email in emails:
            if crm.is_review_reply(email):
                instruction = crm.parse_instruction(email.get('body', ''))
                print(f"解析到指令: {instruction}")
                
    elif args.loop:
        # 启动监听循环
        crm.run_mail_loop()
        
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
