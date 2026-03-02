#!/usr/bin/env python3
"""
智能文章服务 CLI 工具
快速使用文章库和生成文章
"""

import sys
import argparse
from pathlib import Path

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'article_library'))

from article_library.smart_service import SmartArticleService, get_article, generate_and_save


def main():
    parser = argparse.ArgumentParser(
        description='智能文章服务 - 查库或生成微信公众号文章',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 智能判断（查库或生成）
  python3 article_cli.py "给我一篇关于AI学习的文章"
  
  # 强制生成新文章
  python3 article_cli.py "帮我写关于时间管理" --generate
  
  # 生成多篇（默认10篇）
  python3 article_cli.py "职业转型" --generate --count 5
  
  # 查看文章库统计
  python3 article_cli.py --stats
  
  # 启动Web服务
  python3 article_cli.py --serve
        """
    )
    
    parser.add_argument('query', nargs='?', help='用户查询（主题或需求）')
    parser.add_argument('-g', '--generate', action='store_true', 
                       help='强制生成新文章（不查库）')
    parser.add_argument('-c', '--count', type=int, default=10,
                       help='生成文章数量（1-10，默认10）')
    parser.add_argument('-e', '--email', type=str,
                       help='通知邮箱地址')
    parser.add_argument('-s', '--stats', action='store_true',
                       help='查看文章库统计')
    parser.add_argument('--serve', action='store_true',
                       help='启动Web服务')
    parser.add_argument('--mark', type=str, metavar='ARTICLE_ID',
                       help='标记文章审核状态（需配合--status使用）')
    parser.add_argument('--status', type=str, choices=['approved', 'rejected', 'revision'],
                       help='审核状态: approved(通过)/rejected(拒绝)/revision(需修改)')
    parser.add_argument('--notes', type=str, default='',
                       help='审核备注')
    
    args = parser.parse_args()
    
    # 启动Web服务
    if args.serve:
        print("🚀 启动文章管理库 Web 服务...")
        import subprocess
        subprocess.run(['./article_library/start_server.sh', 'start'])
        return
    
    # 查看统计
    if args.stats:
        print("📊 文章库统计")
        print("="*50)
        
        service = SmartArticleService()
        stats = service.get_service_stats()
        
        lib = stats['library']
        print(f"\n文章总数: {lib['total']}")
        print(f"  - 候选文章: {lib['candidates']}")
        print(f"  - 审核通过: {lib['approved']}")
        print(f"  - 已审核: {lib['total_reviewed']}")
        
        if lib.get('topics'):
            print(f"\n主题分布:")
            for topic in lib['topics'][:5]:
                print(f"  - {topic['topic']}: {topic['article_count']}篇")
        
        search = stats.get('search', {})
        if search.get('total_queries'):
            print(f"\n查询统计:")
            print(f"  - 总查询次数: {search['total_queries']}")
            if search.get('feedback'):
                for fb_type, count in search['feedback'].items():
                    print(f"  - {fb_type}: {count}次")
        
        print(f"\n📚 文章库链接: {stats['library_link']}")
        return
    
    # 标记审核状态
    if args.mark and args.status:
        print(f"📝 标记文章 {args.mark} 为 {args.status}")
        
        service = SmartArticleService()
        status_map = {
            'approved': 'approved',
            'rejected': 'rejected',
            'revision': 'revision_needed'
        }
        
        success = service.mark_article_reviewed(
            article_id=args.mark,
            result=status_map[args.status],
            notes=args.notes,
            user_email=args.email
        )
        
        if success:
            print(f"✅ 已标记为 {args.status}")
        else:
            print(f"❌ 标记失败，文章可能不存在")
        return
    
    # 处理文章请求
    if not args.query:
        parser.print_help()
        print("\n❌ 请提供查询内容，或使用 --stats / --serve / --mark")
        return
    
    print(f"🔍 处理请求: {args.query}")
    print(f"   模式: {'强制生成' if args.generate else '智能判断（查库优先）'}")
    if args.generate:
        print(f"   生成数量: {args.count}篇")
    print()
    
    # 调用服务
    result = get_article(
        user_input=args.query,
        user_email=args.email,
        force_generate=args.generate
    )
    
    # 输出结果
    print("\n" + "="*60)
    if result['success']:
        article = result['article']
        print(f"✅ {result['message']}")
        print(f"\n📄 文章信息:")
        print(f"   标题: {article.get('title', 'N/A')}")
        print(f"   主题: {article.get('topic', 'N/A')}")
        print(f"   来源: {'📚 文章库缓存' if result['source'] == 'cache' else '✨ 新生成'}")
        
        if article.get('quality_score'):
            print(f"   质量分: {article['quality_score']:.1f}/10")
        
        if result.get('alternatives'):
            print(f"\n📝 其他候选 ({len(result['alternatives'])}篇):")
            for i, alt in enumerate(result['alternatives'][:3], 1):
                print(f"   {i}. {alt.get('title', 'N/A')[:40]}...")
        
        # 显示文章内容预览
        content = article.get('content', '')
        print(f"\n📖 内容预览:")
        print("-"*60)
        preview = content[:500].replace('\n', ' ')
        print(preview + "..." if len(content) > 500 else preview)
        print("-"*60)
        
        # 显示访问链接
        if article.get('article_id'):
            service = SmartArticleService()
            share_link = service.library.get_share_link(article['article_id'])
            print(f"\n🔗 分享链接: {share_link}")
        
    else:
        print(f"❌ {result['message']}")
    
    print("="*60)


if __name__ == '__main__':
    main()
