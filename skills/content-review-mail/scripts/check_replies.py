#!/usr/bin/env python3
"""
示例：检查审核回复
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from content_review_mail import ContentReviewMail

def main():
    crm = ContentReviewMail()
    
    print("🔍 检查新回复...")
    responses = crm.check_replies()
    
    if not responses:
        print("   暂无新回复")
        return
    
    print(f"   收到 {len(responses)} 条回复\n")
    
    for resp in responses:
        print(f"📧 来自: {resp.get('from', 'Unknown')}")
        print(f"   操作: {resp.get('action', 'UNKNOWN')}")
        print(f"   选择: {resp.get('selected_index', 'N/A')}")
        if resp.get('modifications'):
            print(f"   修改: {resp['modifications'][:100]}...")
        print()

if __name__ == '__main__':
    main()
