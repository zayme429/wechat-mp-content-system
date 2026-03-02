"""
Prompt配置管理器 - 查询推荐专用
"""

import os
import json
from typing import Dict, List

class PromptManager:
    """Prompt配置管理"""
    
    # 查询推荐专用Prompt模板
    DEFAULT_PROMPTS = {
        "intent_recognition": {
            "name": "意图识别",
            "description": "用LLM理解用户查询的真实意图",
            "template": """你是一位专业的保险行业内容分析师。

请分析用户的查询内容，提取以下信息：

用户查询: {{query}}

请输出JSON格式：
{
    "topic": "主题类别（客户经营/保险获客/转介绍/社群营销）",
    "audience": "目标受众（保险代理人/保险客户）",
    "intent_type": "意图类型（方法学习/案例分析/问题解决/经验分享）",
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "urgency": "紧急程度（high/medium/low）",
    "specific_requirements": "用户的具体要求（如：要话术、要案例、要步骤等）"
}

只输出JSON，不要其他内容。""",
            "variables": ["query"],
            "model": "claude-sonnet-4-6"
        },

        "candidate_analysis": {
            "name": "候选文章分析",
            "description": "分析候选文章，给出推荐哪个的结论",
            "template": """你是一位专业的保险内容推荐专家。

用户查询: {{query}}
用户意图: {{intent}}

有以下{{candidate_count}}篇候选文章：

{{candidates_info}}

请分析这些文章，从以下维度评估：
1. 主题相关性（与用户需求匹配度）
2. 内容实用性（是否有可操作的干货）
3. 质量水平（写作质量、案例丰富度）
4. 差异化（与其他候选的区别）

最后给出推荐结论。

输出JSON格式：
{
    "analysis": [
        {
            "article_id": "文章ID",
            "title": "文章标题",
            "scores": {
                "relevance": "相关性分数(1-10)",
                "practicality": "实用性分数(1-10)",
                "quality": "质量分数(1-10)",
                "uniqueness": "差异化分数(1-10)"
            },
            "strengths": ["优点1", "优点2"],
            "weaknesses": ["不足1"]
        }
    ],
    "recommendation": {
        "recommended_id": "推荐的文章ID",
        "reason": "推荐理由（100字以内，说明为什么这篇最适合用户需求）",
        "confidence": "推荐置信度(high/medium/low)"
    }
}

只输出JSON。""",
            "variables": ["query", "intent", "candidate_count", "candidates_info"],
            "model": "claude-sonnet-4-6"
        }
    }
    
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            prompts_dir = os.path.join(base_dir, 'prompts')
        
        self.prompts_dir = prompts_dir
        os.makedirs(prompts_dir, exist_ok=True)
        
        self.custom_prompts = self._load_custom_prompts()
    
    def _load_custom_prompts(self) -> Dict:
        custom_file = os.path.join(self.prompts_dir, 'custom_prompts.json')
        if os.path.exists(custom_file):
            try:
                with open(custom_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_custom_prompts(self):
        custom_file = os.path.join(self.prompts_dir, 'custom_prompts.json')
        with open(custom_file, 'w', encoding='utf-8') as f:
            json.dump(self.custom_prompts, f, ensure_ascii=False, indent=2)
    
    def get_all_prompts(self) -> Dict[str, Dict]:
        all_prompts = {**self.DEFAULT_PROMPTS}
        all_prompts.update(self.custom_prompts)
        return all_prompts
    
    def get_prompt(self, prompt_key: str) -> Dict:
        if prompt_key in self.custom_prompts:
            return self.custom_prompts[prompt_key]
        return self.DEFAULT_PROMPTS.get(prompt_key, {})
    
    def update_prompt(self, prompt_key: str, template: str, name: str = None, 
                     description: str = None, model: str = None) -> bool:
        try:
            self.custom_prompts[prompt_key] = {
                "name": name or self.DEFAULT_PROMPTS.get(prompt_key, {}).get("name", prompt_key),
                "description": description or self.DEFAULT_PROMPTS.get(prompt_key, {}).get("description", ""),
                "template": template,
                "variables": self._extract_variables(template),
                "model": model or "claude-sonnet-4-6"
            }
            self._save_custom_prompts()
            return True
        except Exception as e:
            print(f"保存Prompt失败: {e}")
            return False
    
    def reset_prompt(self, prompt_key: str) -> bool:
        if prompt_key in self.custom_prompts:
            del self.custom_prompts[prompt_key]
            self._save_custom_prompts()
            return True
        return False
    
    def _extract_variables(self, template: str) -> List[str]:
        import re
        variables = re.findall(r'\{\{(\w+)\}\}', template)
        return list(set(variables))
    
    def render_prompt(self, prompt_key: str, variables: Dict) -> str:
        prompt = self.get_prompt(prompt_key)
        template = prompt.get("template", "")
        
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        
        return template


# 全局实例
_prompt_manager = None

def get_prompt_manager() -> PromptManager:
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
