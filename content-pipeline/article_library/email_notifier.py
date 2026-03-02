#!/usr/bin/env python3
"""
文章库邮件通知模块
发送文章库访问链接和文章分享链接
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'src'))

from article_library.library import ArticleLibrary

try:
    from notification.review_mail_sender import ReviewMailSender
except Exception:
    ReviewMailSender = None


class LibraryEmailNotifier:
    """文章库邮件通知器"""

    def __init__(self, library: ArticleLibrary = None, base_url: str = None, smtp_config=None):
        self.library = library or ArticleLibrary()
        self.base_url = base_url or 'http://154.9.252.35:8080'
        self.smtp_config = smtp_config or self._load_smtp_config()

    def _load_smtp_config(self) -> dict:
        # Priority: env > local secrets files
        env_user = (os.environ.get('SMTP_USER') or '').strip() if 'os' in globals() else ''
        env_pass = (os.environ.get('SMTP_PASS') or '').strip() if 'os' in globals() else ''
        if env_user and env_pass:
            return {
                'host': os.environ.get('SMTP_HOST') or 'smtp.example.com',
                'port': int(os.environ.get('SMTP_PORT') or 465),
                'secure': (os.environ.get('SMTP_SECURE') or 'true').lower() in ('1', 'true', 'yes'),
                'user': env_user,
                'pass': env_pass,
                'from': os.environ.get('SMTP_FROM') or env_user,
            }

        for name in ('secrets.local.json', 'secrets.json'):
            p = BASE_DIR / 'config' / name
            if not p.exists():
                continue
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                smtp = data.get('smtp') or {}
                if smtp.get('user') and smtp.get('pass') and not str(smtp.get('pass')).upper().startswith('YOUR_'):
                    return smtp
            except Exception:
                continue
        return {}
    
    def send_library_access_link(self, to_email: str, include_stats: bool = True):
        """
        发送文章库访问链接
        
        Args:
            to_email: 收件人邮箱
            include_stats: 是否包含统计信息
        """
        if not ReviewMailSender or not self.smtp_config:
            print("❌ 邮件功能不可用（缺少 SMTP 配置或 ReviewMailSender）")
            return False

        library_link = self.library.get_library_link(self.base_url)
        
        # 获取统计信息
        stats_content = ""
        if include_stats:
            stats = self.library.get_library_stats()
            stats_content = f"""
<h3>📊 当前文章库统计</h3>
<ul>
    <li><strong>文章总数：</strong>{stats['total']} 篇</li>
    <li><strong>候选文章：</strong>{stats['candidates']} 篇</li>
    <li><strong>审核通过：</strong>{stats['approved']} 篇</li>
    <li><strong>已审核：</strong>{stats['total_reviewed']} 篇</li>
</ul>
"""
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #07c160 0%, #059e4c 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: #f9f9f9; padding: 25px; border-radius: 10px; margin-bottom: 20px; }}
        .button {{ display: inline-block; background: #07c160; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: 500; }}
        .button:hover {{ background: #059e4c; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 8px; }}
        strong {{ color: #07c160; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 微信公众号文章库</h1>
            <p style="margin: 10px 0 0; opacity: 0.9;">您的内容管理中心</p>
        </div>
        
        <div class="content">
            <p>您好！</p>
            <p>您的微信公众号文章库已就绪，点击下方按钮访问：</p>
            
            <div style="text-align: center;">
                <a href="{library_link}" class="button">访问文章库</a>
            </div>
            
            {stats_content}
            
            <p style="margin-top: 20px; color: #666; font-size: 14px;">
                <strong>说明：</strong><br>
                • 文章库存放所有生成的候选文章<br>
                • 候选文章需要您审核后标记状态<br>
                • 审核通过的文章会标记但不会自动发布到公众号<br>
                • 正式发布需要您手动操作
            </p>
        </div>
        
        <div class="footer">
            <p>此邮件由 OpenClaw 内容管理系统自动发送</p>
            <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </div>
</body>
</html>
"""
        
        try:
            sender = ReviewMailSender(self.smtp_config)
            sender.send_html(to_email, "📚 微信公众号文章库访问链接", html_content)
            print(f"✅ 文章库访问链接已发送至 {to_email}")
            return True
        except Exception as e:
            print(f"❌ 发送失败: {e}")
            return False
    
    def send_new_candidates_notification(self, to_email: str, topic: str, 
                                         article_ids: list, candidate_count: int = 3):
        """
        发送新候选文章通知
        
        Args:
            to_email: 收件人邮箱
            topic: 主题
            article_ids: 文章ID列表
            candidate_count: 候选数量
        """
        if not ReviewMailSender or not self.smtp_config:
            print("❌ 邮件功能不可用（缺少 SMTP 配置或 ReviewMailSender）")
            return False

        # 获取文章详情和链接
        articles = []
        for aid in article_ids:
            article = self.library.get_article(aid)
            if article:
                share_link = self.library.get_share_link(aid, self.base_url)
                articles.append({**article, 'share_link': share_link})
        
        # 生成候选列表HTML
        candidates_html = ""
        for i, article in enumerate(articles, 1):
            angle_display = f"<p style='color: #666; margin: 8px 0;'>🎯 <em>{article.get('angle', '')}</em></p>" if article.get('angle') else ""
            score_display = f"<span style='color: #07c160; font-weight: bold;'>质量分: {article.get('quality_score', 0):.1f}</span>" if article.get('quality_score') else ""
            
            candidates_html += f"""
<div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #07c160;">
    <h3 style="margin: 0 0 8px; color: #333;">候选 {i}：{article.get('title', '')}</h3>
    {angle_display}
    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
        {score_display}
        <a href="{article.get('share_link', '#')}" style="background: #07c160; color: white; padding: 6px 15px; text-decoration: none; border-radius: 4px; font-size: 13px;">查看全文</a>
    </div>
</div>
"""
        
        library_link = self.library.get_library_link(self.base_url)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 650px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #07c160 0%, #059e4c 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 25px; }}
        .header h1 {{ margin: 0; font-size: 22px; }}
        .section {{ background: #f9f9f9; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .button {{ display: inline-block; background: #07c160; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 10px 0; font-weight: 500; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
        .instructions {{ background: #fff3e0; padding: 15px; border-radius: 8px; margin-top: 20px; }}
        .instructions h4 {{ margin: 0 0 10px; color: #e65100; }}
        .instructions ol {{ margin: 0; padding-left: 20px; }}
        .instructions li {{ margin-bottom: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📝 新文章候选已生成</h1>
            <p style="margin: 10px 0 0; opacity: 0.9;">主题：{topic}</p>
        </div>
        
        <div class="section">
            <p>已为您生成 <strong>{candidate_count}</strong> 篇候选文章，请查看并选择：</p>
            
            {candidates_html}
            
            <div style="text-align: center; margin-top: 25px;">
                <a href="{library_link}" class="button">查看文章库</a>
            </div>
            
            <div class="instructions">
                <h4>📋 审核说明</h4>
                <ol>
                    <li>点击「查看全文」阅读完整文章</li>
                    <li>选择您满意的候选（记住编号）</li>
                    <li>回复邮件告知我您的选择（如"选候选1"）</li>
                    <li>我会将选中的文章标记为「审核通过」</li>
                    <li>如需修改，请告诉我具体修改意见</li>
                </ol>
                <p style="margin-top: 10px; color: #666; font-size: 13px;">
                    <strong>注意：</strong>审核通过不会自动发布到公众号，仅作标记存储。
                </p>
            </div>
        </div>
        
        <div class="footer">
            <p>此邮件由 OpenClaw 内容管理系统自动发送</p>
            <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </div>
</body>
</html>
"""
        
        try:
            sender = ReviewMailSender(self.smtp_config)
            sender.send_html(to_email, f"📝 新候选文章 - {topic}（共{candidate_count}篇）", html_content)
            print(f"✅ 候选文章通知已发送至 {to_email}")
            return True
        except Exception as e:
            print(f"❌ 发送失败: {e}")
            return False
    
    def send_review_confirmation(self, to_email: str, article_id: str, 
                                  result: str, notes: str = None):
        """
        发送审核确认通知
        
        Args:
            to_email: 收件人邮箱
            article_id: 文章ID
            result: 审核结果
            notes: 审核备注
        """
        if not ReviewMailSender or not self.smtp_config:
            print("❌ 邮件功能不可用（缺少 SMTP 配置或 ReviewMailSender）")
            return False

        article = self.library.get_article(article_id)
        if not article:
            print(f"❌ 文章 {article_id} 不存在")
            return False
        
        share_link = self.library.get_share_link(article_id, self.base_url)
        
        # 结果样式
        if result == 'approved':
            result_text = '✓ 审核通过'
            result_color = '#07c160'
        elif result == 'rejected':
            result_text = '✗ 未通过'
            result_color = '#ff4d4f'
        else:
            result_text = '需要修改'
            result_color = '#faad14'
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: {result_color}; color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 25px; }}
        .header h1 {{ margin: 0; font-size: 22px; }}
        .content {{ background: #f9f9f9; padding: 25px; border-radius: 10px; }}
        .article-box {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        .result-badge {{ display: inline-block; background: {result_color}; color: white; padding: 5px 15px; border-radius: 4px; font-weight: bold; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{result_text}</h1>
            <p style="margin: 10px 0 0; opacity: 0.9;">文章审核状态已更新</p>
        </div>
        
        <div class="content">
            <div class="article-box">
                <h3 style="margin: 0 0 10px;">{article.get('title', '')}</h3>
                <p style="color: #666; margin: 0;">📁 {article.get('topic', '')}</p>
            </div>
            
            <p style="text-align: center; margin: 20px 0;">
                <span class="result-badge">{result_text}</span>
            </p>
            
            {f"<p><strong>审核备注：</strong></p><p style='background: #fff3e0; padding: 12px; border-radius: 6px; color: #666;'>{notes}</p>" if notes else ""}
            
            <div style="text-align: center; margin-top: 25px;">
                <a href="{share_link}" style="background: {result_color}; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block;">查看文章</a>
            </div>
        </div>
        
        <div class="footer">
            <p>此邮件由 OpenClaw 内容管理系统自动发送</p>
            <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </div>
</body>
</html>
"""
        
        try:
            sender = ReviewMailSender(self.smtp_config)
            sender.send_html(to_email, f"{result_text} - {article.get('title', '')[:30]}...", html_content)
            print(f"✅ 审核确认已发送至 {to_email}")
            return True
        except Exception as e:
            print(f"❌ 发送失败: {e}")
            return False


# 便捷函数
def send_library_link(email: str):
    """发送文章库链接"""
    notifier = LibraryEmailNotifier()
    return notifier.send_library_access_link(email)


def notify_new_candidates(email: str, topic: str, article_ids: list):
    """通知新候选文章"""
    notifier = LibraryEmailNotifier()
    return notifier.send_new_candidates_notification(email, topic, article_ids)


if __name__ == '__main__':
    # 测试
    print("🧪 测试文章库邮件通知模块")
    
    notifier = LibraryEmailNotifier()
    
    # 测试发送文章库链接
    # notifier.send_library_access_link("your-email@example.com")
    
    print("✅ 模块加载成功")
    print(f"文章库访问地址: {notifier.base_url}/library")
