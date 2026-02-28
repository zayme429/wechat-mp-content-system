#!/usr/bin/env python3
"""
邮件发送模块 - 发送HTML格式完整文章
已根据反馈优化排版和内容展示
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ReviewMailSender:
    """审核邮件发送器 - 优化版"""
    
    def __init__(self, smtp_config: dict):
        self.smtp = smtp_config
        
    def send_html_review_email(self, to: str, candidates: list, article_date: str,
                               topic_info: dict = None, literature: list = None) -> bool:
        """
        发送HTML格式的审核邮件（完整文章 + 优化排版）

        Args:
            to: 收件人邮箱
            candidates: 候选文章列表（包含完整内容）
            article_date: 文章日期
            topic_info: 主题信息（主题、方向、关键词）
            literature: 文献集合
        """
        try:
            # 构建HTML邮件
            server_email = self.smtp.get('zapier_email', to)
            html = self._build_html_email(candidates, article_date, topic_info, literature, server_email)
            
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'📄 内容审核 - {article_date} ({len(candidates)}篇完整文章)'
            msg['From'] = f"Content Bot <{self.smtp['from']}>"
            msg['To'] = to
            msg['Reply-To'] = self.smtp.get('zapier_email', to)
            server_email = self.smtp.get('zapier_email', to)
            
            msg.attach(MIMEText(html, 'html', 'utf-8'))
            
            # 发送
            server = smtplib.SMTP_SSL(self.smtp['host'], self.smtp['port'])
            server.login(self.smtp['user'], self.smtp['pass'])
            server.sendmail(self.smtp['from'], to, msg.as_string())
            server.quit()
            
            logger.info(f"✅ HTML审核邮件已发送到: {to}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 发送邮件失败: {e}")
            return False
    
    def _build_html_email(self, candidates: list, article_date: str,
                          topic_info: dict = None, literature: list = None,
                          server_email: str = '') -> str:
        """构建HTML邮件内容"""

        # 主题信息 HTML
        topic_html = ""
        if topic_info:
            keywords = ', '.join(topic_info.get('keywords', []))
            direction = topic_info.get('direction', '')
            mode_map = {'manual': '手动指定', 'config': '配置文件', 'auto': '自动热点'}
            mode = mode_map.get(topic_info.get('mode', ''), topic_info.get('mode', ''))
            topic_html = f"""
<div class="topic-box">
    <strong>🎯 本期主题：{topic_info.get('topic', '')}</strong><br>
    <span>确定方式：{mode} | 关键词：{keywords}</span>
    {'<br><span>写作方向：' + direction + '</span>' if direction else ''}
</div>"""

        # 文献集合 HTML
        literature_html = ""
        if literature:
            literature_html = "<div class='literature-box'><strong>📚 文献集合（共{}篇）：</strong><ul>".format(len(literature))
            for i, lit in enumerate(literature, 1):
                url = lit.get('url', '')
                title = lit.get('title', '')
                source = lit.get('source', '')
                summary = lit.get('summary', '')[:100]
                if url:
                    literature_html += f"<li>[{i}] <a href='{url}'>{title}</a>（{source}）<br><small>{summary}</small></li>"
                else:
                    literature_html += f"<li>[{i}] {title}（{source}）<br><small>{summary}</small></li>"
            literature_html += "</ul></div>"

        # 构建候选文章HTML
        candidates_html = ""
        for i, c in enumerate(candidates, 1):
            # 清理内容中的HTML标签防止冲突
            content = c.get('content', '').replace('<', '&lt;').replace('>', '&gt;')

            # 来源信息
            source_news = c.get('source_news', [])
            sources_html = ""
            if source_news:
                sources_html = "<div class='source-box'><strong>📰 参考来源：</strong><ul>"
                for s in source_news:
                    url = s.get('url', '')
                    title = s.get('title', '')
                    source = s.get('source', '')
                    if url:
                        sources_html += f"<li><a href='{url}'>{title}</a>（{source}）</li>"
                    else:
                        sources_html += f"<li>{title}（{source}）</li>"
                sources_html += "</ul></div>"

            # 选题理由
            angle_reason = c.get('angle_reason', '')
            reason_html = f"<div class='reason-box'><strong>💡 选题理由：</strong>{angle_reason}</div>" if angle_reason else ""

            candidates_html += f"""
            <div class="candidate">
                <div class="candidate-header">
                    <h2>候选 {i}：{c['topic']}</h2>
                    <div class="meta">类型：{c.get('angle_type', '标准')} | 字数：{len(content)}字 | 质量分：{c.get('quality_score', 0)}</div>
                </div>
                {sources_html}
                {reason_html}
                <div class="content">{content}</div>
            </div>
            """
        
        # 完整HTML模板
        html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{ 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
    line-height: 1.8; 
    color: #333; 
    max-width: 800px; 
    margin: 0 auto; 
    padding: 20px; 
    background: #f5f7fa; 
}}
.header {{ 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
    color: white; 
    padding: 30px; 
    border-radius: 12px; 
    margin-bottom: 30px; 
    text-align: center; 
}}
.header h1 {{ margin: 0; font-size: 24px; }}
.header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
.info-box {{ 
    background: #e7f3ff; 
    border-left: 4px solid #0066cc; 
    padding: 15px 20px; 
    margin: 20px 0; 
    border-radius: 0 8px 8px 0; 
}}
.candidate {{ 
    background: white; 
    border-radius: 12px; 
    padding: 25px; 
    margin: 20px 0; 
    box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
}}
.candidate-header {{ 
    border-bottom: 2px solid #667eea; 
    padding-bottom: 15px; 
    margin-bottom: 20px; 
}}
.candidate h2 {{ 
    color: #667eea; 
    margin: 0 0 10px 0; 
    font-size: 20px; 
}}
.candidate .meta {{ 
    color: #666; 
    font-size: 14px; 
    margin-bottom: 15px; 
}}
.candidate .content {{ 
    font-size: 15px; 
    color: #444; 
    white-space: pre-wrap; 
    line-height: 1.8;
}}
.source-box {{
    background: #f0f7ff;
    border-left: 3px solid #4a9eff;
    padding: 10px 15px;
    margin: 10px 0;
    border-radius: 0 6px 6px 0;
    font-size: 13px;
}}
.source-box ul {{
    margin: 5px 0 0 0;
    padding-left: 20px;
}}
.source-box a {{
    color: #0066cc;
    text-decoration: none;
}}
.reason-box {{
    background: #f6fff0;
    border-left: 3px solid #52c41a;
    padding: 10px 15px;
    margin: 10px 0;
    border-radius: 0 6px 6px 0;
    font-size: 13px;
    color: #555;
}}
.actions {{ 
    background: #fff3cd; 
    border-left: 4px solid #ffc107; 
    padding: 20px; 
    margin: 30px 0; 
    border-radius: 0 8px 8px 0; 
}}
.actions h3 {{ margin-top: 0; color: #856404; }}
.actions code {{ 
    background: #f8f9fa; 
    padding: 2px 8px; 
    border-radius: 4px; 
    font-family: monospace; 
    font-size: 14px; 
}}
.footer {{ 
    margin-top: 40px; 
    padding-top: 20px; 
    border-top: 2px solid #ddd; 
    color: #999; 
    font-size: 13px; 
    text-align: center; 
}}
.topic-box {{
    background: #f0f4ff;
    border-left: 4px solid #667eea;
    padding: 15px 20px;
    margin: 20px 0;
    border-radius: 0 8px 8px 0;
    font-size: 14px;
}}
.literature-box {{
    background: #fafafa;
    border: 1px solid #e8e8e8;
    border-radius: 8px;
    padding: 15px 20px;
    margin: 20px 0;
    font-size: 13px;
}}
.literature-box ul {{
    margin: 8px 0 0 0;
    padding-left: 20px;
}}
.literature-box li {{
    margin-bottom: 8px;
    line-height: 1.6;
}}
.literature-box a {{
    color: #0066cc;
    text-decoration: none;
}}
.literature-box small {{
    color: #888;
    display: block;
}}
</style>
</head>
<body>
<div class="header">
    <h1>📄 内容审核通知</h1>
    <p>{article_date} | {len(candidates)}篇候选文章 | 请审核后回复</p>
</div>

<div class="info-box">
    <strong>💡 系统工作流说明：</strong><br>
    • 内容偏好：实战派、配置代码、成本数据（根据反馈固化）<br>
    • 反馈机制：自动记录选择，优化后续生成
</div>

<div style="background:#fff3cd;border-left:4px solid #ffc107;padding:15px 20px;margin:20px 0;border-radius:0 8px 8px 0;font-size:15px;">
    <strong>📩 审核回复方式：</strong><br>
    请新建邮件发送到 <a href="mailto:{server_email}"><strong>{server_email}</strong></a><br>
    <small>（直接回复此邮件可能无法被系统接收）</small><br><br>
    回复格式：<code>选A</code> / <code>选B</code> / <code>选C</code>，可附加修改意见
</div>

{topic_html}

{literature_html}

{candidates_html}

<div class="actions">
    <h3>🎯 审核操作指南</h3>
    <p><strong>直接回复此邮件即可：</strong></p>
    <p>• <code>发布 1</code> / <code>发布 2</code> / <code>发布 3</code> — 发布指定候选到微信公众号</p>
    <p>• <code>重新生成 [方向描述]</code> — 按新方向重写（如：重新生成 更侧重实操案例）</p>
    <p>• <code>修改 1 [意见]</code> — 针对性优化（如：修改 1 增加数据支撑）</p>
    <p>• <code>跳过</code> — 今日不发布</p>
</div>

<div class="footer">
    <p>AI内容自动生成系统 v2.0 | 生成时间：{article_date}</p>
    <p>总字数：{sum(len(c.get('content','')) for c in candidates)} 字</p>
</div>
</body>
</html>
"""
        return html


# 兼容性：保留旧的方法名
def send_review_email(to: str, candidates: list, article_date: str, smtp_config: dict) -> bool:
    """兼容旧调用的函数"""
    sender = ReviewMailSender(smtp_config)
    return sender.send_html_review_email(to, candidates, article_date)


if __name__ == '__main__':
    # 测试
    config = {
        'host': 'smtp.163.com',
        'port': 465,
        'user': '13257667003@163.com',
        'pass': 'XUnhjmQwxUa7pKFt',
        'from': '13257667003@163.com'
    }
    
    test_candidates = [
        {
            'topic': '测试文章1',
            'angle_type': '实战派',
            'quality_score': 8.5,
            'content': '这是测试内容...'
        }
    ]
    
    sender = ReviewMailSender(config)
    sender.send_html_review_email('test@example.com', test_candidates, '20260226')
