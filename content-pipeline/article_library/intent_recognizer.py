#!/usr/bin/env python3
"""
用户意图识别模块
调用Kimi判断用户是想要查库还是生成新文章
"""

import os
import json
import re
from typing import Dict, Optional
from datetime import datetime

class IntentRecognizer:
    """用户意图识别器"""
    
    def __init__(self):
        self.api_key = os.environ.get('MOONSHOT_API_KEY') or self._load_api_key()
        self.api_base = "https://api.moonshot.cn/v1"
    
    def _load_api_key(self) -> str:
        """从配置文件加载API Key"""
        try:
            config_path = '/root/.openclaw/openclaw.json'
            with open(config_path) as f:
                config = json.load(f)
                return config.get('models', {}).get('providers', {}).get('moonshot', {}).get('apiKey', '')
        except:
            return ''
    
    def _call_kimi(self, prompt: str, temperature: float = 0.3) -> str:
        """调用Kimi API"""
        try:
            import urllib.request
            
            data = json.dumps({
                'model': 'moonshot-v1-8k',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': temperature
            }).encode()
            
            req = urllib.request.Request(
                f'{self.api_base}/chat/completions',
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                }
            )
            
            with urllib.request.urlopen(req, timeout=30) as r:
                result = json.loads(r.read())
                return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"⚠️ Kimi调用失败: {e}")
            return ''
    
    def recognize(self, user_input: str, context: Dict = None) -> Dict:
        """
        识别用户意图
        
        Args:
            user_input: 用户输入
            context: 上下文信息（可选）
            
        Returns:
            {
                'intent': 'search' | 'generate' | 'unclear',
                'topic': 提取的主题,
                'requirements': {
                    'style': 风格偏好,
                    'angle': 角度偏好,
                    'length': 字数要求,
                    'other': 其他要求
                },
                'confidence': 置信度,
                'reason': 判断理由
            }
        """
        # 先进行简单规则判断（快速路径）
        rule_result = self._rule_based_check(user_input)
        if rule_result['intent'] != 'unclear' and rule_result['confidence'] > 0.8:
            return rule_result
        
        # 调用Kimi进行深度理解
        prompt = f"""你是一位智能助手，需要判断用户想要什么。

用户输入：{user_input!r}

请分析用户的意图，并输出以下格式的JSON：

{{
    "intent": "search" 或 "generate",
    "topic": "提取的主题/关键词",
    "requirements": {{
        "style": "风格要求（如有）",
        "angle": "角度要求（如有）",
        "length": "字数要求（如有）",
        "other": "其他特殊要求"
    }},
    "confidence": 0.0-1.0,
    "reason": "判断理由"
}}

判断规则：
- "search"（查库）：用户想要找已有的文章，如"给我一篇关于xxx的文章"、"有没有写过xxx"
- "generate"（生成）：用户明确要求写新文章，如"写一篇关于xxx的文章"、"帮我写xxx"、"生成xxx"
- 如果用户输入很模糊，无法判断，返回"unclear"

只输出JSON，不要其他内容。"""

        response = self._call_kimi(prompt)
        
        # 解析JSON
        try:
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response)
            
            # 确保字段完整
            result.setdefault('intent', 'unclear')
            result.setdefault('topic', '')
            result.setdefault('requirements', {})
            result.setdefault('confidence', 0.5)
            result.setdefault('reason', '')
            
            # 标准化intent
            if result['intent'] not in ['search', 'generate', 'unclear']:
                result['intent'] = 'unclear'
            
            return result
            
        except json.JSONDecodeError:
            # JSON解析失败，返回规则判断结果
            return rule_result
    
    def _rule_based_check(self, user_input: str) -> Dict:
        """
        基于规则的快速意图判断
        """
        text = user_input.lower().strip()
        
        # 明确生成意图的关键词
        generate_keywords = [
            '写一篇', '帮我写', '生成', '创作', '新写', '重新写',
            'write a', 'generate', 'create', 'compose',
            '再写一篇', '换个', '新的'
        ]
        
        # 明确查库意图的关键词
        search_keywords = [
            '有没有', '之前', '写过', '查找', '搜索', '找一下',
            '给我一篇', '推荐一篇', '现有的', '库里的',
            'have you written', 'previous', 'existing'
        ]
        
        # 强制生成关键词（最高优先级）
        force_generate = ['必须新写', '强制生成', '不要库里的', '不要旧的']
        
        result = {
            'intent': 'unclear',
            'topic': '',
            'requirements': {},
            'confidence': 0.5,
            'reason': ''
        }
        
        # 检查强制生成
        for kw in force_generate:
            if kw in text:
                result['intent'] = 'generate'
                result['confidence'] = 1.0
                result['reason'] = f'包含强制生成关键词: {kw}'
                return result
        
        # 检查生成关键词
        for kw in generate_keywords:
            if kw in text:
                result['intent'] = 'generate'
                result['confidence'] = 0.9
                result['reason'] = f'包含生成关键词: {kw}'
                return result
        
        # 检查查库关键词
        for kw in search_keywords:
            if kw in text:
                result['intent'] = 'search'
                result['confidence'] = 0.9
                result['reason'] = f'包含查库关键词: {kw}'
                return result
        
        # 提取主题（简单规则）
        topic_patterns = [
            r'关于(.+?)的',
            r'(.+?)方面',
            r'(.+?)主题',
            r'(.+?)文章'
        ]
        for pattern in topic_patterns:
            match = re.search(pattern, user_input)
            if match:
                result['topic'] = match.group(1).strip()
                break
        
        return result
    
    def extract_topic_from_empty_input(self, user_profile: Dict = None) -> Dict:
        """
        当用户没有输入时，基于热点/节日/用户特点生成主题
        
        Args:
            user_profile: 用户画像（可选）
            
        Returns:
            {
                'topic': 生成的主题,
                'reason': 生成理由,
                'source': 'hotspot'|'holiday'|'profile'|'general'
            }
        """
        from datetime import datetime
        
        now = datetime.now()
        
        # 检查节日
        holiday_topics = self._check_holiday(now)
        if holiday_topics:
            return {
                'topic': holiday_topics[0],
                'reason': f'基于即将到来的节日',
                'source': 'holiday'
            }
        
        # 获取热点（简化实现）
        hotspot = self._get_hotspot_topic()
        if hotspot:
            return {
                'topic': hotspot,
                'reason': '基于当前热点',
                'source': 'hotspot'
            }
        
        # 基于用户画像（如果有）
        if user_profile and user_profile.get('interests'):
            return {
                'topic': f"关于{user_profile['interests'][0]}的深度思考",
                'reason': '基于您的兴趣偏好',
                'source': 'profile'
            }
        
        # 默认主题
        return {
            'topic': 'AI时代的学习方法论',
            'reason': '默认推荐主题',
            'source': 'general'
        }
    
    def _check_holiday(self, now: datetime) -> list:
        """检查近期节日"""
        # 简化的节日映射
        holidays = {
            (1, 1): ['新年规划：AI如何帮你制定年度计划'],
            (2, 14): ['情人节特辑：AI时代的亲密关系'],
            (5, 1): ['劳动节：AI如何改变工作方式'],
            (6, 1): ['儿童节：AI时代的教育变革'],
            (9, 10): ['教师节：AI辅助教学的新范式'],
            (10, 1): ['国庆特辑：AI发展的中国路径'],
            (12, 25): ['年终总结：AI如何提升复盘效率'],
        }
        
        # 检查今天及未来7天
        for i in range(7):
            check_date = now.replace(day=now.day + i)
            if (check_date.month, check_date.day) in holidays:
                return holidays[(check_date.month, check_date.day)]
        
        return []
    
    def _get_hotspot_topic(self) -> str:
        """获取热点主题（简化实现）"""
        # 可以集成RSS或新闻API
        # 这里返回一个默认的通用热点
        return 'ChatGPT一周年：AI应用的反思与展望'


# 便捷函数
def recognize_intent(user_input: str, context: Dict = None) -> Dict:
    """便捷的意图识别函数"""
    recognizer = IntentRecognizer()
    return recognizer.recognize(user_input, context)


def generate_topic_for_empty_input(user_profile: Dict = None) -> Dict:
    """为用户生成主题（当用户没有输入时）"""
    recognizer = IntentRecognizer()
    return recognizer.extract_topic_from_empty_input(user_profile)


if __name__ == '__main__':
    # 测试
    print("🧪 测试意图识别模块")
    
    recognizer = IntentRecognizer()
    
    test_cases = [
        "给我一篇关于AI学习的文章",
        "帮我写一篇关于职业转型的文章",
        "有没有写过认知升级的文章？",
        "重新写一篇，不要库里的",
        "生成一篇新的",
        ""  # 空输入
    ]
    
    for text in test_cases:
        print(f"\n输入: '{text}'")
        if text:
            result = recognizer.recognize(text)
            print(f"  意图: {result['intent']}")
            print(f"  主题: {result['topic']}")
            print(f"  置信度: {result['confidence']}")
            print(f"  理由: {result['reason']}")
        else:
            result = recognizer.extract_topic_from_empty_input()
            print(f"  生成主题: {result['topic']}")
            print(f"  来源: {result['source']}")
    
    print("\n✅ 测试完成")
