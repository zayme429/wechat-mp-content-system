#!/usr/bin/env python3
"""
邮件通知系统
用于审核通知、报告发送
"""

import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import List, Dict

class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = Path('/root/.openclaw/workspace/content-pipeline/config/email.json')
        
        self.config = self._load_config(config_path)
        self.template_dir = Path('/root/.openclaw/workspace/content-pipeline/config/email_templates')
        self.template_dir.mkdir(exist_ok=True)
    
    def _load_config(self, config_path: Path) -> Dict:
        """加载邮件配置"""
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 默认配置
        return {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': '',
            'password': '',
            'from_email': '',
            'to_email': '',
            'enabled': False
        }
    
    def send_review_notification(self, candidates: List[Dict], 
                                article_date: str,
                                preview_length: int = 500) -> bool:
        """发送审核通知邮件"""
        
        if not self.config['enabled']:
            print("⚠️ 邮件通知未启用")
            return False
        
        subject = f"📄 内容审核 - {article_date} ({len(candidates)}个候选)"
        
        # 构建邮件内容
        html_content = self._build_review_email(candidates, article_date, preview_length)
        
        return self._send_email(subject, html_content, is_html=True)
    
    def _build_review_email(self, candidates: List[Dict], 
                           article_date: str,
                           preview_length: int) -> str:
        """构建审核邮件HTML"""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
                .candidate {{ background: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
                .candidate h2 {{ margin-top: 0; color: #667eea; font-size: 18px; }}
                .meta {{ display: flex; gap: 20px; margin: 10px 0; font-size: 14px; color: #666; }}
                .meta span {{ background: #e9ecef; padding: 4px 12px; border-radius: 20px; }}
                .preview {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #dee2e6; }}
                .actions {{ margin: 20px 0; padding: 20px; background: #e7f3ff; border-radius: 8px; }}
                .actions h3 {{ margin-top: 0; color: #0066cc; }}
                .action-list {{ list-style: none; padding: 0; }}
                .action-list li {{ padding: 8px 0; border-bottom: 1px solid #ddd; }}
                .action-list code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
                .footer {{ margin-top: 40px; padding-top: 20px; border-top: 2px solid #eee; color: #999; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📄 内容审核通知</h1>
                <p>今日已生成 {len(candidates)} 个候选文章，请选择最佳版本或提出修改意见</p>
            </div>
            
            <div class="candidates">
        """
        
        for i, c in enumerate(candidates, 1):
            preview = c['content'][:preview_length] + '...' if len(c['content']) > preview_length else c['content']
            
            html += f"""
                <div class="candidate">
                    <h2>候选 {i}: {c['topic']}</h2>
                    <div class="meta">
                        <span>角度: {c['angle_type']}</span>
                        <span>质量分: {c['quality_score']:.1f}/10</span>
                        <span>独特分: {c['uniqueness_score']:.1f}/10</span>
                        <span>字数: {c['word_count']}</span>
                    </div>
                    <div class="preview">
                        <strong>预览:</strong><br>
                        {preview.replace(chr(10), '<br>')}
                    </div>
                </div>
            """
        
        html += f"""
            </div>
            
            <div class="actions">
                <h3>🎯 审核操作指南</h3>
                <ul class="action-list">
                    <li><strong>选择发布:</strong> 回复邮件 <code>发布 [候选编号]</code> (如: 发布 2)</li>
                    <li><strong>重新生成:</strong> 回复 <code>重新生成 [方向描述]</code> (如: 重新生成 更侧重实操案例)</li>
                    <li><strong>修改优化:</strong> 回复 <code>修改 [候选编号] [具体要求]</code> (如: 修改 1 增加更多数据支撑)</li>
                    <li><strong>跳过今日:</strong> 回复 <code>跳过</code></li>
                    <li><strong>查看完整:</strong> 回复 <code>查看 [候选编号]</code></li>
                </ul>
                <p><strong>截止时间:</strong> 24小时内未回复将自动选择最高分候选发布</p>
            </div>
            
            <div class="footer">
                <p>AI内容自动生成系统 | 生成时间: {article_date}</p>
                <p>如需调整审核偏好或查看历史，请回复 <code>配置</code></p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_weekly_report(self, stats: Dict) -> bool:
        """发送周报"""
        
        if not self.config['enabled']:
            return False
        
        subject = f"📊 内容生产周报 - {stats['week_range']}"
        
        html = f"""
        <h2>📊 本周内容生产报告</h2>
        
        <h3>📈 数据概览</h3>
        <ul>
            <li>生成文章数: {stats.get('article_count', 0)}</li>
            <li>平均质量分: {stats.get('avg_quality', 0):.1f}</li>
            <li>平均独特分: {stats.get('avg_uniqueness', 0):.1f}</li>
            <li>用户反馈数: {stats.get('feedback_count', 0)}</li>
        </ul>
        
        <h3>📝 已固化的改进</h3>
        <ul>
        """
        
        for improvement in stats.get('improvements', []):
            html += f"<li>{improvement}</li>"
        
        html += """
        </ul>
        
        <h3>📚 本周热门主题</h3>
        <ul>
        """
        
        for topic in stats.get('top_topics', []):
            html += f"<li>{topic}</li>"
        
        html += """
        </ul>
        """
        
        return self._send_email(subject, html, is_html=True)
    
    def _send_email(self, subject: str, content: str, is_html: bool = False) -> bool:
        """发送邮件"""
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['from_email']
            msg['To'] = self.config['to_email']
            msg['Subject'] = subject
            
            if is_html:
                msg.attach(MIMEText(content, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # 连接SMTP服务器
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls()
            server.login(self.config['username'], self.config['password'])
            
            # 发送
            server.send_message(msg)
            server.quit()
            
            print(f"✅ 邮件已发送: {subject}")
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False

if __name__ == '__main__':
    # 测试
    notifier = EmailNotifier()
    
    # 测试数据
    test_candidates = [
        {
            'topic': '测试主题1',
            'angle_type': '实战派',
            'quality_score': 8.5,
            'uniqueness_score': 7.5,
            'word_count': 1500,
            'content': '这是测试内容...' * 50
        },
        {
            'topic': '测试主题2', 
            'angle_type': '深度派',
            'quality_score': 7.5,
            'uniqueness_score': 8.5,
            'word_count': 1800,
            'content': '这是测试内容...' * 50
        }
    ]
    
    # 生成邮件内容预览
    html = notifier._build_review_email(test_candidates, '2026-02-26', 300)
    
    # 保存预览
    preview_file = Path('/root/.openclaw/workspace/content-pipeline/web/email_preview.html')
    preview_file.parent.mkdir(exist_ok=True)
    with open(preview_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 邮件预览已保存: {preview_file}")
    print("请在浏览器中查看")
