#!/usr/bin/env python3
"""
智能文章服务主控制器
整合意图识别、文章检索、文章生成、文章库管理
"""

import sys
from pathlib import Path
from typing import Dict, Optional, List

sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')
sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline/article_library')

from article_library.library import ArticleLibrary
from article_library.search_engine import ArticleSearchEngine
from article_library.intent_recognizer import IntentRecognizer
from article_library.diverse_generator import DiverseArticleGenerator
from article_library.email_notifier import LibraryEmailNotifier


class SmartArticleService:
    """
    智能文章服务
    
    核心逻辑：
    1. 识别用户意图（查库 vs 生成）
    2. 如果是查库 → 先检索文章库
    3. 如果检索命中 → 返回文章（标记来源：缓存）
    4. 如果未命中或意图是生成 → 生成新文章
    5. 生成的新文章保存到库中
    """
    
    def __init__(self):
        self.library = ArticleLibrary()
        self.search_engine = ArticleSearchEngine(self.library)
        self.intent_recognizer = IntentRecognizer()
        self.generator = DiverseArticleGenerator()
        self.notifier = LibraryEmailNotifier(self.library)
        
        print("✅ 智能文章服务初始化完成")
    
    def handle_request(
        self,
        user_input: str,
        user_email: str = None,
        force_generate: bool = False,
        user_id: str = None,
    ) -> Dict:
        """
        处理用户请求
        
        Args:
            user_input: 用户输入
            user_email: 用户邮箱（用于通知）
            force_generate: 是否强制生成（覆盖意图识别）
            
        Returns:
            {
                'success': bool,
                'source': 'cache' | 'generated',
                'article': 文章数据,
                'alternatives': 其他候选（如果是生成的）,
                'message': 说明信息
            }
        """
        print(f"\n{'='*60}")
        print(f"📨 用户请求: {user_input or '(空输入)'}")
        print(f"{'='*60}")
        
        # 步骤1: 意图识别
        print("\n🔍 步骤1: 识别用户意图...")
        
        if force_generate:
            intent_result = {
                'intent': 'generate',
                'topic': user_input,
                'requirements': {},
                'confidence': 1.0,
                'reason': '用户强制生成'
            }
        elif not user_input or user_input.strip() == '':
            # 空输入，自动生成主题
            topic_gen = self.intent_recognizer.extract_topic_from_empty_input()
            intent_result = {
                'intent': 'generate',
                'topic': topic_gen['topic'],
                'requirements': {},
                'confidence': 0.8,
                'reason': topic_gen['reason']
            }
        else:
            intent_result = self.intent_recognizer.recognize(user_input)
        
        print(f"  意图: {intent_result['intent']}")
        print(f"  主题: {intent_result['topic']}")
        print(f"  置信度: {intent_result['confidence']}")
        print(f"  理由: {intent_result['reason']}")
        
        # 步骤2: 根据意图处理
        if intent_result['intent'] == 'search':
            # 意图是查库
            return self._handle_search_intent(intent_result, user_email)
        
        elif intent_result['intent'] == 'generate':
            # 意图是生成
            return self._handle_generate_intent(intent_result, user_email)
        
        else:
            # 意图不明确，尝试查库，未命中则生成
            print("\n⚠️ 意图不明确，先尝试查库...")
            search_result = self._handle_search_intent(intent_result, user_email)
            if search_result['success']:
                return search_result
            else:
                print("  查库未命中，转为生成")
                return self._handle_generate_intent(intent_result, user_email, user_id=user_id)
    
    def _handle_search_intent(self, intent_result: Dict, user_email: str = None) -> Dict:
        """处理查库意图"""
        print("\n📚 步骤2: 检索文章库...")
        
        query = intent_result['topic']
        
        # 搜索文章库
        article = self.search_engine.search(query)
        
        if article:
            # 命中缓存
            print(f"\n✅ 命中文章库缓存")
            
            result = {
                'success': True,
                'source': 'cache',
                'article': article,
                'alternatives': [],
                'message': f'从文章库为您找到一篇相关文章（来源：缓存）'
            }
            
            # 发送通知（可选）
            if user_email:
                share_link = self.library.get_share_link(article['article_id'])
                print(f"\n📧 文章链接: {share_link}")
            
            return result
        
        else:
            # 未命中
            print("\n❌ 文章库未命中")
            return {
                'success': False,
                'source': None,
                'article': None,
                'alternatives': [],
                'message': '文章库中没有匹配的文章'
            }
    
    def _handle_generate_intent(self, intent_result: Dict, user_email: str = None, user_id: str = None) -> Dict:
        """处理生成意图"""
        print("\n✍️ 步骤2: 生成新文章...")
        
        topic = intent_result['topic']
        
        # 解析生成数量要求
        count = self._extract_count_from_requirements(intent_result.get('requirements', {}))
        print(f"  将生成 {count} 篇候选文章")
        
        # 生成文章（按用户标题风格区分）
        generator = self.generator
        if user_id:
            generator = DiverseArticleGenerator(user_id=user_id)
        candidates = generator.generate_custom_count(topic, count=count)
        
        if not candidates:
            return {
                'success': False,
                'source': None,
                'article': None,
                'alternatives': [],
                'message': '文章生成失败'
            }
        
        # 保存到文章库
        print("\n💾 步骤3: 保存到文章库...")
        article_ids = self._save_candidates_to_library(candidates)
        print(f"  已保存 {len(article_ids)} 篇候选")
        
        # 为每篇文章建立搜索索引
        print("\n📇 步骤4: 建立搜索索引...")
        for i, (article_id, candidate) in enumerate(zip(article_ids, candidates)):
            self.search_engine.index_article(
                article_id=article_id,
                content=candidate['content'],
                topic=candidate['topic'],
                angle=candidate['angle']
            )
            if i == 0:
                print(f"  已为文章建立索引")
        
        # 发送通知邮件
        if user_email:
            print(f"\n📧 步骤5: 发送通知邮件到 {user_email}...")
            self.notifier.send_new_candidates_notification(
                to_email=user_email,
                topic=topic,
                article_ids=article_ids,
                candidate_count=len(candidates)
            )
        
        # 返回结果
        best = candidates[0]  # 质量最高的
        alternatives = candidates[1:] if len(candidates) > 1 else []
        
        return {
            'success': True,
            'source': 'generated',
            'article': {
                'article_id': article_ids[0],
                'title': best['title'],
                'content': best['content'],
                'topic': best['topic'],
                'angle': best['angle'],
                'quality_score': best['quality_score']
            },
            'alternatives': [
                {
                    'article_id': article_ids[i+1],
                    'title': alt['title'],
                    'angle': alt['angle'],
                    'quality_score': alt['quality_score']
                }
                for i, alt in enumerate(alternatives)
            ],
            'message': f'已为您生成 {len(candidates)} 篇新文章（来源：新生成）'
        }
    
    def _extract_count_from_requirements(self, requirements: Dict) -> int:
        """从需求中提取生成数量"""
        # 默认生成10篇
        default_count = 10
        
        # 检查其他要求字段
        other = requirements.get('other', '')
        
        # 尝试提取数字
        import re
        match = re.search(r'(\d+)\s*篇', other)
        if match:
            count = int(match.group(1))
            return min(count, 10)  # 最多10篇
        
        return default_count
    
    def _save_candidates_to_library(self, candidates: List[Dict]) -> List[str]:
        """保存候选到文章库"""
        candidates_data = []
        for c in candidates:
            candidates_data.append({
                'title': c['title'],
                'content': c['content'],
                'angle': c['angle'],
                'quality_score': c['quality_score']
            })
        
        if candidates_data:
            topic = candidates[0]['topic']
            return self.library.save_candidates_batch(topic, candidates_data)
        
        return []
    
    def get_article_by_id(self, article_id: str) -> Optional[Dict]:
        """通过ID获取文章"""
        return self.library.get_article(article_id)
    
    def mark_article_reviewed(self, article_id: str, result: str, 
                              notes: str = None, user_email: str = None) -> bool:
        """
        标记文章审核状态
        
        Args:
            article_id: 文章ID
            result: 'approved'/'rejected'/'revision_needed'
            notes: 备注
            user_email: 用户邮箱
        """
        success = self.library.mark_reviewed(
            article_id, result, notes,
            performed_by=user_email or 'user'
        )
        
        if success and user_email:
            self.notifier.send_review_confirmation(
                user_email, article_id, result, notes
            )
        
        return success
    
    def record_feedback(self, article_id: str, feedback: str):
        """记录用户反馈"""
        self.search_engine.record_feedback(article_id, feedback)
    
    def get_service_stats(self) -> Dict:
        """获取服务统计"""
        library_stats = self.library.get_library_stats()
        search_stats = self.search_engine.get_search_stats()
        
        return {
            'library': library_stats,
            'search': search_stats,
            'library_link': self.library.get_library_link()
        }


# 便捷函数
def get_article(user_input: str, user_email: str = None, 
                force_generate: bool = False) -> Dict:
    """
    便捷函数：获取文章
    
    使用示例:
        result = get_article("给我一篇关于AI学习的文章")
        if result['success']:
            print(result['article']['content'])
    """
    service = SmartArticleService()
    return service.handle_request(user_input, user_email, force_generate)


def generate_and_save(topic: str, count: int = 10, user_email: str = None) -> Dict:
    """
    便捷函数：强制生成新文章并保存
    
    使用示例:
        result = generate_and_save("AI学习方法论", count=5)
    """
    service = SmartArticleService()
    intent = {
        'intent': 'generate',
        'topic': topic,
        'requirements': {'other': f'{count}篇'},
        'confidence': 1.0,
        'reason': '强制生成'
    }
    return service._handle_generate_intent(intent, user_email)


if __name__ == '__main__':
    # 测试
    print("🧪 测试智能文章服务")
    
    service = SmartArticleService()
    
    # 测试1: 查库意图
    print("\n" + "="*60)
    print("测试1: 用户想要查库")
    result = service.handle_request("给我一篇关于AI学习的文章")
    print(f"\n结果: {result['message']}")
    print(f"来源: {result['source']}")
    
    # 测试2: 生成意图
    print("\n" + "="*60)
    print("测试2: 用户想要生成（使用测试主题）")
    # 这里用一个小主题测试，避免生成太久
    result = service.handle_request("帮我写一篇关于时间管理的文章", force_generate=True)
    print(f"\n结果: {result['message']}")
    print(f"来源: {result['source']}")
    if result['success']:
        print(f"生成 {len(result['alternatives']) + 1} 篇候选")
    
    # 查看统计
    print("\n" + "="*60)
    print("服务统计:")
    stats = service.get_service_stats()
    print(f"文章库: {stats['library']['total']} 篇")
    print(f"审核通过: {stats['library']['approved']} 篇")
    
    print("\n✅ 测试完成")
