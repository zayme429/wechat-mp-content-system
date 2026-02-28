#!/usr/bin/env python3
"""
示例：处理回复邮件
"""

import sys
sys.path.insert(0, '../..')

from scripts.content_review_mail import ContentReviewMail

# 初始化
crm = ContentReviewMail()

print("检查新邮件...")

# 检查新邮件
emails = crm.check_new_emails()

if not emails:
    print("没有新邮件")
else:
    print(f"找到 {len(emails)} 封新邮件")
    
    for email in emails:
        print(f"\n主题: {email.get('subject', 'N/A')}")
        print(f"发件人: {email.get('from', 'N/A')}")
        
        # 判断是否是审核回复
        if crm.is_review_reply(email):
            print("✅ 这是审核回复邮件")
            
            # 解析指令
            instruction = crm.parse_instruction(email.get('body', ''))
            print(f"\n解析到指令:")
            print(f"  动作: {instruction.get('action')}")
            print(f"  候选: {instruction.get('candidate')}")
            print(f"  方向: {instruction.get('direction')}")
            print(f"  反馈: {instruction.get('feedback')}")
            
            # 处理指令
            print("\n执行指令...")
            crm.handle_instruction(instruction, email)
            
            # 发送确认回复
            reply_content = f"已收到您的指令: {instruction.get('action')}\n\n正在处理中，请稍候..."
            crm.send_reply_email(
                to=email.get('from', ''),
                subject=f"Re: {email.get('subject', '')}",
                content=reply_content
            )
        else:
            print("❌ 这不是审核回复邮件")
