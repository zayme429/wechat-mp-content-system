#!/usr/bin/env python3
"""
示例：发送内容审核邮件
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from content_review_mail import ContentReviewMail

def main():
    crm = ContentReviewMail()
    
    # 准备候选文章
    candidates = [
        {
            'topic': 'AI Agent 的未来：从工具到伙伴',
            'angle_type': '深度分析',
            'quality_score': 8.5,
            'uniqueness_score': 8.0,
            'word_count': 1500,
            'content': '''人工智能代理（AI Agent）正在经历从简单工具到智能伙伴的转变。

在过去的一年中，我们看到了显著的技术进步...

[完整文章内容]'''
        },
        {
            'topic': '为什么你的 AI Agent 还不够聪明',
            'angle_type': '实战指南',
            'quality_score': 7.8,
            'uniqueness_score': 7.5,
            'word_count': 1200,
            'content': '''很多企业在使用 AI Agent 时都会遇到一个共同的问题...

[完整文章内容]'''
        }
    ]
    
    to_email = crm.config['review'].get('default_recipient')
    
    # 发送审核邮件
    result = crm.send_review_email(
        to=to_email,
        subject='【待审核】AI Agent 发展趋势',
        candidates=candidates,
        article_date=__import__('datetime').datetime.now().strftime('%Y-%m-%d')
    )
    
    print(f"✅ 邮件已发送")
    print(f"   主题: AI Agent 发展趋势")
    print(f"   候选数: {len(candidates)}")
    print(f"   收件人: {to_email}")

if __name__ == '__main__':
    main()
