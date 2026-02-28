"""
Prompt配置管理器
支持意图识别、匹配度计算、推荐理由等Prompt的自定义
"""

import os
import json
from typing import Dict, List

class PromptManager:
    """Prompt配置管理"""
    
    # 默认Prompt模板
    DEFAULT_PROMPTS = {
        "intent_recognition": {
            "name": "意图识别",
            "description": "识别用户查询的意图，提取主题、受众等信息",
            "template": """你是一位专业的保险行业内容分析师。

请分析用户的查询内容，提取以下信息：

用户查询: {{query}}

请输出JSON格式：
{
    "topic": "主题类别（如：客户经营、保险获客、转介绍等）",
    "audience": "目标受众（如：保险代理人、保险客户）",
    "intent_type": "意图类型（如：方法学习、案例分析、问题解决）",
    "keywords": ["关键词1", "关键词2"],
    "urgency": "紧急程度（high/medium/low）"
}

只输出JSON，不要其他内容。""",
            "variables": ["query"],
            "model": "kimi-k2.5"
        },
        
        "match_scoring": {
            "name": "匹配度计算",
            "description": "计算查询与文章的匹配分数",
            "template": """你是一位内容匹配专家。

请评估以下查询与文章的匹配程度：

用户查询: {{query}}
查询意图: {{intent}}

文章标题: {{title}}
文章内容预览: {{content_preview}}
文章主题: {{topic}}
文章角度: {{angle_type}}
文章质量分: {{quality_score}}

请从以下维度评估匹配度（1-10分）：
1. 主题相关性（查询主题与文章主题的匹配度）
2. 内容适配性（文章内容是否能满足查询需求）
3. 质量匹配（文章质量是否符合查询的专业度要求）

输出JSON格式：
{
    "total_score": "总分（1-10）",
    "dimension_scores": {
        "topic_relevance": "主题相关性得分",
        "content_fit": "内容适配性得分",
        "quality_match": "质量匹配得分"
    },
    "reason": "评分理由（简短说明）"
}

只输出JSON。""",
            "variables": ["query", "intent", "title", "content_preview", "topic", "angle_type", "quality_score"],
            "model": "kimi-k2.5"
        },
        
        "recommendation_reason": {
            "name": "推荐理由生成",
            "description": "生成为什么推荐这篇文章的理由",
            "template": """你是一位专业的内容推荐师。

请为用户生成推荐这篇文章的理由：

用户查询: {{query}}
用户意图: {{intent}}

推荐文章标题: {{title}}
文章主题: {{topic}}
文章角度: {{angle_type}}
匹配度分数: {{match_score}}

请生成一段简短的推荐理由（50字以内），说明为什么这篇文章适合用户的需求。
要求：
1. 突出文章与用户需求的相关性
2. 提及文章的核心价值
3. 语言亲切自然

直接输出推荐理由，不要其他内容。""",
            "variables": ["query", "intent", "title", "topic", "angle_type", "match_score"],
            "model": "kimi-k2.5"
        },
        
        "content_generation": {
            "name": "文章内容生成",
            "description": "根据主题和角度生成保险行业文章",
            "template": """你是一位资深保险行业内容创作者。

【写作任务】
主题：{{topic}}
角度：{{angle}}
目标受众：保险代理人

【写作要求】
1. 字数：1200-1800字
2. 避免技术术语（如：数字化、SaaS、CRM、私域流量等）
3. 使用保险行业通俗用语（如：跟进、回访、约访、促成、缘故客户等）
4. 必须包含：
   - 具体案例或场景
   - 可直接使用的话术或方法
   - 清晰的步骤或要点
5. 语言风格：接地气、像有经验的保险代理人在分享经验

【内容结构】
- 开头：场景引入或问题抛出
- 中间：案例分析 + 方法讲解 + 话术示范
- 结尾：总结要点 + 行动建议

请直接输出文章内容（不要标题）。""",
            "variables": ["topic", "angle"],
            "model": "kimi-k2.5"
        }
    }
    
    def __init__(self, prompts_dir: str = None):
        """初始化Prompt管理器"""
        if prompts_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            prompts_dir = os.path.join(base_dir, 'prompts')
        
        self.prompts_dir = prompts_dir
        os.makedirs(prompts_dir, exist_ok=True)
        
        # 加载自定义Prompt
        self.custom_prompts = self._load_custom_prompts()
    
    def _load_custom_prompts(self) -> Dict:
        """加载用户自定义Prompt"""
        custom_file = os.path.join(self.prompts_dir, 'custom_prompts.json')
        if os.path.exists(custom_file):
            try:
                with open(custom_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_custom_prompts(self):
        """保存自定义Prompt"""
        custom_file = os.path.join(self.prompts_dir, 'custom_prompts.json')
        with open(custom_file, 'w', encoding='utf-8') as f:
            json.dump(self.custom_prompts, f, ensure_ascii=False, indent=2)
    
    def get_all_prompts(self) -> Dict[str, Dict]:
        """获取所有Prompt（默认 + 自定义）"""
        all_prompts = {**self.DEFAULT_PROMPTS}
        all_prompts.update(self.custom_prompts)
        return all_prompts
    
    def get_prompt(self, prompt_key: str) -> Dict:
        """获取指定Prompt"""
        # 优先使用自定义
        if prompt_key in self.custom_prompts:
            return self.custom_prompts[prompt_key]
        return self.DEFAULT_PROMPTS.get(prompt_key, {})
    
    def update_prompt(self, prompt_key: str, template: str, name: str = None, 
                     description: str = None, model: str = None) -> bool:
        """更新Prompt"""
        try:
            self.custom_prompts[prompt_key] = {
                "name": name or self.DEFAULT_PROMPTS.get(prompt_key, {}).get("name", prompt_key),
                "description": description or self.DEFAULT_PROMPTS.get(prompt_key, {}).get("description", ""),
                "template": template,
                "variables": self._extract_variables(template),
                "model": model or "kimi-k2.5",
                "updated_at": datetime.now().isoformat()
            }
            self._save_custom_prompts()
            return True
        except Exception as e:
            print(f"保存Prompt失败: {e}")
            return False
    
    def reset_prompt(self, prompt_key: str) -> bool:
        """重置为默认Prompt"""
        if prompt_key in self.custom_prompts:
            del self.custom_prompts[prompt_key]
            self._save_custom_prompts()
            return True
        return False
    
    def _extract_variables(self, template: str) -> List[str]:
        """从模板中提取变量"""
        import re
        variables = re.findall(r'\{\{(\w+)\}\}', template)
        return list(set(variables))
    
    def render_prompt(self, prompt_key: str, variables: Dict) -> str:
        """渲染Prompt（替换变量）"""
        prompt = self.get_prompt(prompt_key)
        template = prompt.get("template", "")
        
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        
        return template
    
    def validate_template(self, template: str) -> tuple[bool, str]:
        """验证模板格式"""
        # 检查是否有变量
        variables = self._extract_variables(template)
        if not variables:
            return False, "模板中没有定义变量（使用 {{variable}} 格式）"
        
        # 检查JSON格式（如果是JSON输出模板）
        if "json" in template.lower():
            try:
                # 简单检查JSON格式
                if '"' in template and '{' in template:
                    return True, "模板格式正确"
            except:
                pass
        
        return True, "模板格式正确"
    
    def export_prompts(self) -> str:
        """导出所有Prompt为JSON字符串"""
        return json.dumps(self.get_all_prompts(), ensure_ascii=False, indent=2)
    
    def import_prompts(self, json_str: str) -> bool:
        """导入Prompt"""
        try:
            prompts = json.loads(json_str)
            for key, value in prompts.items():
                if key not in self.DEFAULT_PROMPTS:  # 不覆盖默认
                    self.custom_prompts[key] = value
            self._save_custom_prompts()
            return True
        except Exception as e:
            print(f"导入失败: {e}")
            return False


# 全局实例
_prompt_manager = None

def get_prompt_manager() -> PromptManager:
    """获取全局Prompt管理器"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


if __name__ == '__main__':
    from datetime import datetime
    
    pm = get_prompt_manager()
    print("📝 Prompt管理器")
    print(f"\n可用Prompt:")
    for key, info in pm.get_all_prompts().items():
        print(f"  - {key}: {info['name']}")
        print(f"    变量: {', '.join(info['variables'])}")
    
    # 测试渲染
    print("\n测试渲染 intent_recognition:")
    rendered = pm.render_prompt("intent_recognition", {"query": "客户经营技巧"})
    print(rendered[:200] + "...")
