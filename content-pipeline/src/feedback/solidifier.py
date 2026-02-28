#!/usr/bin/env python3
"""
反馈固化系统
学习用户反馈，自动更新提示词和配置
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict

class FeedbackSolidifier:
    """反馈固化器"""
    
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = Path('/root/.openclaw/workspace/content-pipeline')
        self.base_dir = base_dir
        self.feedback_file = base_dir / 'feedback' / 'feedback_log.json'
        self.feedback_file.parent.mkdir(exist_ok=True)
        
        # 加载历史反馈
        self.feedback_history = self._load_feedback_history()
    
    def _load_feedback_history(self) -> List[Dict]:
        """加载反馈历史"""
        if self.feedback_file.exists():
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_feedback_history(self):
        """保存反馈历史"""
        with open(self.feedback_file, 'w', encoding='utf-8') as f:
            json.dump(self.feedback_history, f, ensure_ascii=False, indent=2)
    
    def record_feedback(self, article_id: str, stage: str, 
                       feedback_type: str, content: str,
                       severity: str = 'medium'):
        """记录反馈"""
        feedback = {
            'id': len(self.feedback_history) + 1,
            'article_id': article_id,
            'stage': stage,
            'type': feedback_type,
            'content': content,
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
            'addressed': False,
            'solidified': False
        }
        
        self.feedback_history.append(feedback)
        self._save_feedback_history()
        
        # 立即分析并尝试固化
        self._analyze_and_solidify(feedback)
    
    def _analyze_and_solidify(self, feedback: Dict):
        """分析反馈并固化"""
        content = feedback['content']
        feedback_type = feedback['type']
        
        # 提取关键词和模式
        patterns = self._extract_patterns(content)
        
        # 根据反馈类型处理
        if feedback_type == '风格问题':
            self._solidify_style_preference(patterns, content)
        elif feedback_type == '内容方向':
            self._solidify_content_direction(patterns, content)
        elif feedback_type == '结构问题':
            self._solidify_structure_preference(patterns, content)
        elif feedback_type == '质量问题':
            self._solidify_quality_standard(patterns, content)
        
        # 标记为已固化
        feedback['solidified'] = True
        self._save_feedback_history()
    
    def _extract_patterns(self, content: str) -> List[str]:
        """从反馈中提取模式"""
        patterns = []
        
        # 常见反馈模式
        pattern_keywords = {
            '避免': 'avoid_pattern',
            '不要': 'avoid_pattern',
            '太': 'degree_pattern',
            '不够': 'degree_pattern',
            '缺少': 'missing_pattern',
            '需要': 'requirement_pattern',
            '应该': 'suggestion_pattern'
        }
        
        for keyword, pattern_type in pattern_keywords.items():
            if keyword in content:
                # 提取关键词前后的上下文
                idx = content.find(keyword)
                start = max(0, idx - 10)
                end = min(len(content), idx + 20)
                context = content[start:end]
                patterns.append({
                    'type': pattern_type,
                    'context': context,
                    'keyword': keyword
                })
        
        return patterns
    
    def _solidify_style_preference(self, patterns: List[Dict], content: str):
        """固化风格偏好"""
        # 读取当前风格配置
        system_config = self._load_system_config()
        
        # 提取"避免"的内容
        avoid_patterns = [p for p in patterns if p['type'] == 'avoid_pattern']
        for p in avoid_patterns:
            avoid_item = p['context'].replace('避免', '').replace('不要', '').strip()
            if avoid_item and avoid_item not in system_config['content_preferences']['avoid']:
                system_config['content_preferences']['avoid'].append(avoid_item)
                print(f"📝 已固化风格偏好: 避免 '{avoid_item}'")
        
        # 提取" tone"偏好
        if ' tone' in content or '语气' in content or '风格' in content:
            # 提取语气描述
            tone_keywords = ['理性', '克制', '温暖', '犀利', '幽默', '严肃']
            for tone in tone_keywords:
                if tone in content and tone not in system_config['content_preferences']['tone']:
                    system_config['content_preferences']['tone'].append(tone)
                    print(f"📝 已固化风格偏好: 语气 '{tone}'")
        
        self._save_system_config(system_config)
    
    def _solidify_content_direction(self, patterns: List[Dict], content: str):
        """固化内容方向"""
        system_config = self._load_system_config()
        
        # 提取感兴趣的方向
        direction_keywords = ['多写', '关注', '重点', '深入']
        for keyword in direction_keywords:
            if keyword in content:
                # 提取方向
                idx = content.find(keyword)
                end = min(len(content), idx + 30)
                direction = content[idx:end].replace(keyword, '').strip()
                
                # 添加到主题库
                pillars = system_config['content_strategy']['pillar_topics']
                if direction and len(direction) > 3:
                    # 检查是否已存在
                    exists = any(p['name'] == direction for p in pillars)
                    if not exists:
                        pillars.append({
                            'id': f'custom_{len(pillars)}',
                            'name': direction,
                            'weight': 15,
                            'last_used': None,
                            'performance_score': 0
                        })
                        print(f"📝 已固化内容方向: '{direction}'")
        
        self._save_system_config(system_config)
    
    def _solidify_structure_preference(self, patterns: List[Dict], content: str):
        """固化结构偏好"""
        system_config = self._load_system_config()
        
        # 结构相关的反馈
        structure_keywords = {
            '开头': 'introduction',
            '结尾': 'conclusion',
            '案例': 'case_study',
            '数据': 'data',
            '建议': 'actionable_advice'
        }
        
        for keyword, element in structure_keywords.items():
            if keyword in content:
                if '需要' in content or '要' in content:
                    # 需要更多
                    if element not in system_config['content_preferences']['must_include']:
                        system_config['content_preferences']['must_include'].append(element)
                        print(f"📝 已固化结构偏好: 必须包含 '{keyword}'")
        
        self._save_system_config(system_config)
    
    def _solidify_quality_standard(self, patterns: List[Dict], content: str):
        """固化质量标准"""
        system_config = self._load_system_config()
        
        # 字数要求
        word_count_match = re.search(r'(\d+)字', content)
        if word_count_match:
            count = int(word_count_match.group(1))
            system_config['quality_criteria']['min_word_count'] = min(count, 1000)
            system_config['quality_criteria']['max_word_count'] = max(count + 500, 2000)
            print(f"📝 已固化质量标准: 字数 {count}±")
        
        self._save_system_config(system_config)
    
    def _load_system_config(self) -> Dict:
        """加载系统配置"""
        config_file = self.base_dir / 'config' / 'content_system.json'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'content_preferences': {'avoid': [], 'tone': [], 'must_include': []}}
    
    def _save_system_config(self, config: Dict):
        """保存系统配置"""
        config_file = self.base_dir / 'config' / 'content_system.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def generate_feedback_report(self, days: int = 7) -> str:
        """生成反馈报告"""
        recent = [f for f in self.feedback_history 
                 if (datetime.now() - datetime.fromisoformat(f['timestamp'])).days <= days]
        
        if not recent:
            return "近期无反馈"
        
        report = f"## 近{days}天反馈报告\n\n"
        report += f"总反馈数: {len(recent)}\n\n"
        
        # 按类型统计
        type_counts = {}
        for f in recent:
            t = f['type']
            type_counts[t] = type_counts.get(t, 0) + 1
        
        report += "### 反馈类型分布\n"
        for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            report += f"- {t}: {count}条\n"
        
        # 已固化的偏好
        solidified = [f for f in recent if f['solidified']]
        report += f"\n### 已固化的改进 ({len(solidified)}条)\n"
        for f in solidified[-5:]:
            report += f"- {f['content'][:50]}...\n"
        
        return report

if __name__ == '__main__':
    solidifier = FeedbackSolidifier()
    
    # 测试记录反馈
    solidifier.record_feedback('test_001', '初稿审核', '风格问题', 
                              '避免过度使用技术术语，应该更接地气')
    
    print("\n" + solidifier.generate_feedback_report())
