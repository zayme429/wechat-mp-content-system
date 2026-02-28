#!/usr/bin/env python3
"""
文章库 Pipeline 集成
将文章库功能集成到内容生成流程中
"""

import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')
sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline/article_library')

from article_library.library import ArticleLibrary
from article_library.email_notifier import LibraryEmailNotifier


class PipelineLibraryIntegration:
    """Pipeline 与文章库集成"""
    
    def __init__(self, library: ArticleLibrary = None, notifier: LibraryEmailNotifier = None):
        self.library = library or ArticleLibrary()
        self.notifier = notifier or LibraryEmailNotifier(self.library)
    
    def save_candidates_from_generation(self, topic: str, candidates_data: List[Dict],
                                         user_email: str = None) -> Dict:
        """
        保存生成的候选文章到文章库
        
        Args:
            topic: 文章主题
            candidates_data: 候选数据列表，每项包含title/content/angle等
            user_email: 用户邮箱（用于发送通知）
            
        Returns:
            操作结果，包含article_ids和分享链接
        """
        print(f"\n💾 正在将 {len(candidates_data)} 篇候选保存到文章库...")
        
        # 标准化候选数据
        normalized_candidates = []
        for i, candidate in enumerate(candidates_data, 1):
            normalized_candidates.append({
                'title': candidate.get('title', f'{topic} - 候选{i}'),
                'content': candidate.get('content', candidate.get('article', '')),
                'angle': candidate.get('angle', candidate.get('approach', '')),
                'quality_score': candidate.get('quality_score', 
                    candidate.get('evaluation', {}).get('total_score', 0) / 10 if isinstance(candidate.get('evaluation'), dict) else None)
            })
        
        # 批量保存到文章库
        article_ids = self.library.save_candidates_batch(topic, normalized_candidates)
        
        print(f"✅ 已保存 {len(article_ids)} 篇候选")
        
        # 生成分享链接
        share_links = []
        for aid in article_ids:
            link = self.library.get_share_link(aid)
            share_links.append(link)
            print(f"   - {aid}")
        
        # 发送通知邮件
        if user_email:
            print(f"\n📧 发送通知邮件到 {user_email}...")
            self.notifier.send_new_candidates_notification(
                to_email=user_email,
                topic=topic,
                article_ids=article_ids,
                candidate_count=len(candidates_data)
            )
        
        return {
            'article_ids': article_ids,
            'share_links': share_links,
            'library_link': self.library.get_library_link()
        }
    
    def process_user_review_response(self, response_text: str, user_email: str = None) -> Dict:
        """
        处理用户的审核回复
        
        Args:
            response_text: 用户回复内容（如"选候选1"、"都拒绝"、"文章ID xxx 通过"）
            user_email: 用户邮箱
            
        Returns:
            处理结果
        """
        import re
        
        result = {
            'action': None,
            'article_id': None,
            'success': False,
            'message': ''
        }
        
        # 解析用户回复
        text = response_text.lower().strip()
        
        # 模式1: "选候选1" / "选择候选2" / "要候选3"
        candidate_match = re.search(r'(选|选择|要|喜欢).*候选\s*(\d)', text)
        if candidate_match:
            candidate_num = int(candidate_match.group(2))
            result['action'] = 'select_candidate'
            result['candidate_num'] = candidate_num
            result['message'] = f'用户选择候选 {candidate_num}'
            
            # 查找最近的候选文章
            recent = self.library.list_articles(status='candidate', limit=10)
            candidates = [a for a in recent if a.get('candidate_num') == candidate_num]
            
            if candidates:
                article_id = candidates[0]['article_id']
                self.library.mark_reviewed(article_id, 'approved', 
                    notes=f'用户选择候选{candidate_num}',
                    performed_by=user_email or 'user')
                result['article_id'] = article_id
                result['success'] = True
                
                # 发送确认
                if user_email:
                    self.notifier.send_review_confirmation(
                        user_email, article_id, 'approved',
                        notes=f'已标记为审核通过（用户选择候选{candidate_num}）'
                    )
            else:
                result['message'] = f'未找到候选 {candidate_num}'
        
        # 模式2: "拒绝" / "都不满意" / "重新生成"
        elif any(kw in text for kw in ['拒绝', '不要', '不满意', '重新', '再来']):
            result['action'] = 'reject_all'
            result['message'] = '用户拒绝所有候选，需要重新生成'
            result['success'] = True
            
            # 标记最近的候选为拒绝
            recent = self.library.list_articles(status='candidate', limit=10)
            for article in recent:
                self.library.mark_reviewed(
                    article['article_id'], 'rejected',
                    notes='用户拒绝，需重新生成',
                    performed_by=user_email or 'user'
                )
        
        # 模式3: 直接指定文章ID
        # "文章ID xxx 通过" / "标记 xxx 为通过"
        id_match = re.search(r'(?:文章id|id|标记)\s*[:：]?\s*([a-z0-9_]+).*?(通过|批准|同意)', text)
        if id_match:
            article_id = id_match.group(1)
            result['action'] = 'approve_by_id'
            result['article_id'] = article_id
            
            success = self.library.mark_reviewed(
                article_id, 'approved',
                notes='用户直接批准',
                performed_by=user_email or 'user'
            )
            result['success'] = success
            result['message'] = f'文章 {article_id} 已标记为审核通过' if success else f'文章 {article_id} 不存在'
            
            if success and user_email:
                self.notifier.send_review_confirmation(
                    user_email, article_id, 'approved'
                )
        
        # 模式4: 修改建议
        # "修改xxx" / "xxx需要调整"
        elif any(kw in text for kw in ['修改', '调整', '改']):
            result['action'] = 'request_revision'
            result['message'] = '用户提出修改建议'
            result['success'] = True
            
            # 提取修改建议
            revision_notes = response_text
            
            # 标记最近的候选为需要修改
            recent = self.library.list_articles(status='candidate', limit=3)
            for article in recent:
                self.library.mark_reviewed(
                    article['article_id'], 'revision_needed',
                    notes=revision_notes,
                    performed_by=user_email or 'user'
                )
        
        return result
    
    def get_library_summary(self) -> Dict:
        """获取文章库概览"""
        stats = self.library.get_library_stats()
        recent_approved = self.library.list_articles(
            status='reviewed_approved', limit=5
        )
        
        return {
            'stats': stats,
            'recent_approved': recent_approved,
            'library_link': self.library.get_library_link()
        }
    
    def export_approved_articles(self) -> List[Dict]:
        """导出所有审核通过的文章"""
        return self.library.list_articles(status='reviewed_approved', limit=1000)


# 便捷函数
def integrate_with_pipeline(topic: str, candidates: List[Dict], email: str = None):
    """
    与Pipeline集成的便捷函数
    
    使用示例:
        from article_library.pipeline_integration import integrate_with_pipeline
        
        result = integrate_with_pipeline(
            topic="AI学习方法论",
            candidates=[
                {'title': '...', 'content': '...', 'angle': '...'},
                {...},
                {...}
            ],
            email="user@example.com"
        )
        
        # result包含:
        # - article_ids: 文章ID列表
        # - share_links: 分享链接列表
        # - library_link: 文章库访问链接
    """
    integration = PipelineLibraryIntegration()
    return integration.save_candidates_from_generation(topic, candidates, email)


def handle_user_response(response: str, email: str = None):
    """处理用户审核回复的便捷函数"""
    integration = PipelineLibraryIntegration()
    return integration.process_user_review_response(response, email)


if __name__ == '__main__':
    # 测试集成
    print("🧪 测试 Pipeline 文章库集成")
    
    integration = PipelineLibraryIntegration()
    
    # 测试数据
    test_candidates = [
        {
            'title': 'AI时代的学习革命：从被动接受到主动构建',
            'content': '# 文章内容1\n\n这是一篇关于AI学习方法论的文章...',
            'angle': '强调学习方式的转变',
            'quality_score': 8.5
        },
        {
            'title': '认知升级：AI如何重塑我们的思维模式',
            'content': '# 文章内容2\n\n这是另一篇关于认知升级的文章...',
            'angle': '聚焦认知层面的影响',
            'quality_score': 7.8
        },
        {
            'title': 'AI工具提效：从工具使用者到思维共创者',
            'content': '# 文章内容3\n\n这是关于AI工具提效的文章...',
            'angle': '侧重工具应用与实践',
            'quality_score': 8.2
        }
    ]
    
    # 测试保存候选（不发送邮件）
    print("\n--- 测试保存候选 ---")
    result = integration.save_candidates_from_generation(
        topic="AI学习方法论",
        candidates_data=test_candidates,
        user_email=None  # 不发送邮件测试
    )
    
    print(f"\n✅ 保存成功")
    print(f"文章库链接: {result['library_link']}")
    print(f"\n分享链接:")
    for link in result['share_links']:
        print(f"  - {link}")
    
    # 测试处理用户回复
    print("\n--- 测试处理用户回复 ---")
    
    # 模拟用户选择候选1
    response_result = integration.process_user_review_response("选候选1")
    print(f"\n用户回复: '选候选1'")
    print(f"处理结果: {response_result}")
    
    # 查看库统计
    print("\n--- 文章库统计 ---")
    summary = integration.get_library_summary()
    stats = summary['stats']
    print(f"总数: {stats['total']}")
    print(f"候选: {stats['candidates']}")
    print(f"通过: {stats['approved']}")
    print(f"已审核: {stats['total_reviewed']}")
    
    print("\n✅ 集成测试完成")
