#!/usr/bin/env python3
"""
多候选内容生成器
一次生成多个版本供选择
"""

import json
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))
from generator.content_generator import ContentGenerator

class MultiCandidateGenerator:
    """多候选生成器"""
    
    def __init__(self):
        self.base_generator = ContentGenerator()
        self.variation_prompts = self._load_variation_prompts()
    
    def _load_variation_prompts(self) -> Dict:
        """加载不同变体的提示词策略"""
        return {
            'angle_variations': [
                {
                    'name': '实战派',
                    'focus': '具体工具、操作步骤、可复现案例',
                    'style': '实用、接地气、手把手教学'
                },
                {
                    'name': '深度派',
                    'focus': '底层逻辑、本质分析、长期趋势',
                    'style': '理性、宏观、哲思'
                },
                {
                    'name': '故事派',
                    'focus': '人物经历、转型故事、情感共鸣',
                    'style': '叙事、有温度、启发性'
                }
            ],
            'depth_variations': [
                {'name': '入门版', 'target': 'AI新手', 'complexity': '低'},
                {'name': '进阶版', 'target': '有一定基础者', 'complexity': '中'},
                {'name': '专家版', 'target': '行业从业者', 'complexity': '高'}
            ]
        }
    
    def generate_candidates(self, news_items: List[Dict], 
                          recent_topics: List[str],
                          count: int = 3) -> List[Dict]:
        """生成多个候选"""
        
        print(f"🎯 生成 {count} 个候选版本...")
        
        candidates = []
        
        # 候选1: 实战派角度
        candidate1 = self._generate_with_angle(
            news_items, recent_topics,
            self.variation_prompts['angle_variations'][0]
        )
        candidates.append(candidate1)
        
        # 候选2: 深度派角度
        if count >= 2:
            candidate2 = self._generate_with_angle(
                news_items, recent_topics,
                self.variation_prompts['angle_variations'][1]
            )
            candidates.append(candidate2)
        
        # 候选3: 故事派角度
        if count >= 3:
            candidate3 = self._generate_with_angle(
                news_items, recent_topics,
                self.variation_prompts['angle_variations'][2]
            )
            candidates.append(candidate3)
        
        return candidates
    
    def _generate_with_angle(self, news_items: List[Dict],
                            recent_topics: List[str],
                            angle_config: Dict) -> Dict:
        """使用特定角度生成"""
        
        # 构建角度特定的提示词
        angle_prompt = f"""
基于以下热点资讯，从"{angle_config['name']}"角度撰写文章：

角度特点：{angle_config['focus']}
写作风格：{angle_config['style']}

热点资讯：
{self._format_news(news_items)}

要求：
1. 严格遵循"{angle_config['name']}"的风格定位
2. 必须包含具体案例和数据
3. 1500-2000字
4. 拒绝陈词滥调

请输出：
选题标题：[标题]
核心角度：[一句话概括]
文章内容：[完整文章]
"""
        
        # 调用LLM
        content = self.base_generator._call_llm(angle_prompt, temperature=1)
        
        # 解析结果
        lines = content.strip().split('\n')
        title = ''
        angle = ''
        article_content = ''
        
        for i, line in enumerate(lines):
            if '选题标题：' in line or '选题标题:' in line:
                title = line.split('：', 1)[-1].split(':', 1)[-1].strip()
            elif '核心角度：' in line or '核心角度:' in line:
                angle = line.split('：', 1)[-1].split(':', 1)[-1].strip()
            elif '文章内容：' in line or '文章内容:' in line:
                article_content = '\n'.join(lines[i+1:])
                break
        
        # 如果没找到标记，取前3行作为元信息，后面作为内容
        if not article_content and len(lines) > 3:
            title = lines[0][:50] if not title else title
            angle = lines[1][:50] if not angle else angle
            article_content = '\n'.join(lines[2:])
        
        # 计算质量分数（简化版）
        quality_score = self._calculate_quality_score(article_content)
        uniqueness_score = self._calculate_uniqueness_score(article_content, recent_topics)
        
        return {
            'topic': title or f'{angle_config["name"]}视角文章',
            'angle': angle or angle_config['name'],
            'content': article_content or content,
            'angle_type': angle_config['name'],
            'quality_score': quality_score,
            'uniqueness_score': uniqueness_score,
            'word_count': len(article_content or content),
            # 来源溯源信息
            'source_news': [{'title': n['title'], 'source': n['source'], 'url': n.get('url', '')} for n in news_items[:3]],
            'angle_reason': f"基于{angle_config['name']}策略：{angle_config['focus']}",
        }
    
    def _format_news(self, news_items: List[Dict]) -> str:
        """格式化新闻列表"""
        text = ""
        for i, item in enumerate(news_items[:5], 1):
            text += f"\n{i}. {item['title']} ({item['source']})"
        return text
    
    def _calculate_quality_score(self, content: str) -> float:
        """计算内容质量分数"""
        score = 5.0  # 基础分
        
        # 检查必备元素
        if '案例' in content or '例子' in content:
            score += 1
        if '%' in content or '数据' in content:
            score += 1
        if '建议' in content or '方法' in content:
            score += 1
        if len(content) >= 1200:
            score += 1
        if '?' in content or '？' in content:
            score += 0.5  # 有提问，有互动感
        
        return min(score, 10)
    
    def _calculate_uniqueness_score(self, content: str, recent_topics: List[str]) -> float:
        """计算独特性分数"""
        score = 7.0  # 基础分
        
        # 检查与近期主题的相似度
        content_lower = content.lower()
        for topic in recent_topics[-10:]:
            if topic.lower() in content_lower:
                score -= 0.5
        
        # 检查是否有新鲜观点
        fresh_terms = ['新范式', '重构', '跃迁', '本质', '底层', '第一性']
        for term in fresh_terms:
            if term in content:
                score += 0.3
        
        return max(min(score, 10), 1)

if __name__ == '__main__':
    generator = MultiCandidateGenerator()
    
    # 测试
    test_news = [
        {'title': 'GitHub发布Agentic Workflows', 'source': '机器之心'},
        {'title': 'OpenAI新功能上线', 'source': 'InfoQ'}
    ]
    
    candidates = generator.generate_candidates(test_news, [], count=3)
    
    for i, c in enumerate(candidates, 1):
        print(f"\n{'='*60}")
        print(f"候选 {i}: {c['topic']}")
        print(f"角度: {c['angle']}")
        print(f"质量分: {c['quality_score']}, 独特分: {c['uniqueness_score']}")
        print(f"字数: {c['word_count']}")
