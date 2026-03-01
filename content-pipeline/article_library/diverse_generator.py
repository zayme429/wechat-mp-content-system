#!/usr/bin/env python3
"""
多样化文章生成器
基于主题生成10篇不同角度、风格的文章
"""

import sys
from pathlib import Path
from typing import List, Dict
import json

sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')
sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline/src')

from generator.content_generator import ContentGenerator

class DiverseArticleGenerator:
    """多样化文章生成器"""
    
    # 10种不同的写作角度
    ANGLES = [
        {
            'name': '实战派',
            'desc': '注重实操方法，给出具体可执行的步骤',
            'tone': '实用、直接',
            'structure': '问题→方法→步骤→案例→总结'
        },
        {
            'name': '深度派',
            'desc': '深入分析本质，提供底层逻辑思考',
            'tone': '思辨、深入',
            'structure': '现象→分析→原理→洞察→启示'
        },
        {
            'name': '故事派',
            'desc': '用故事案例带出观点，易读有趣',
            'tone': '叙事、温暖',
            'structure': '故事→冲突→转折→启示→行动'
        },
        {
            'name': '数据派',
            'desc': '用数据说话，强调证据和统计',
            'tone': '客观、理性',
            'structure': '数据→趋势→解读→预测→建议'
        },
        {
            'name': '批判派',
            'desc': '质疑现状，指出问题，提出改进',
            'tone': '犀利、建设',
            'structure': '现状→问题→批判→重构→方案'
        },
        {
            'name': '趋势派',
            'desc': '着眼未来，预测发展方向',
            'tone': '前瞻、洞察',
            'structure': '回顾→现状→趋势→预测→准备'
        },
        {
            'name': '跨界派',
            'desc': '跨领域视角，类比其他行业',
            'tone': '开阔、联想',
            'structure': '领域A→领域B→类比→启发→应用'
        },
        {
            'name': '极简派',
            'desc': '化繁为简，提炼核心要点',
            'tone': '简洁、清晰',
            'structure': '复杂→拆解→核心→简化→实践'
        },
        {
            'name': '反常识派',
            'desc': '挑战常规认知，提供新视角',
            'tone': '颠覆、启发',
            'structure': '常识→质疑→新视角→论证→应用'
        },
        {
            'name': '体系派',
            'desc': '构建知识框架，系统讲解',
            'tone': '系统、完整',
            'structure': '框架→模块→关联→应用→总结'
        }
    ]
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.generator = ContentGenerator()
        self.config = self._load_config()
        self._style_instructions = self._load_article_style_instructions()
    
    def _load_config(self) -> Dict:
        """加载配置"""
        config_path = Path('/root/.openclaw/workspace/content-pipeline/config/content_system.json')
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {}
    
    def generate_diverse_candidates(self, topic: str, count: int = 10, 
                                    literature: List[Dict] = None) -> List[Dict]:
        """
        生成多样化的候选文章
        
        Args:
            topic: 主题
            count: 生成数量（默认10）
            literature: 参考资料
            
        Returns:
            候选文章列表
        """
        print(f"\n🎯 为主题「{topic}」生成 {count} 篇多样化文章")
        
        candidates = []
        
        # 选择角度
        selected_angles = self.ANGLES[:count]
        
        for i, angle_def in enumerate(selected_angles, 1):
            print(f"\n  生成候选 {i}/{count}: {angle_def['name']}风格")
            
            # 构建提示词
            prompt = self._build_prompt(topic, angle_def, literature)
            
            # 生成文章
            content = self.generator._call_llm(prompt)
            
            # 评估质量
            quality_score = self._evaluate_quality(content)
            
            # 提取标题
            title = self._extract_title(content, topic, angle_def['name'])
            
            candidate = {
                'title': title,
                'topic': topic,
                'angle': angle_def['desc'],
                'angle_type': angle_def['name'],
                'content': content,
                'quality_score': quality_score,
                'word_count': len(content),
                'structure': angle_def['structure'],
                'tone': angle_def['tone']
            }
            
            candidates.append(candidate)
            print(f"    ✓ 完成，质量分: {quality_score:.1f}")
        
        # 按质量分排序
        candidates.sort(key=lambda x: x['quality_score'], reverse=True)
        
        print(f"\n✅ 生成完成，平均质量分: {sum(c['quality_score'] for c in candidates)/len(candidates):.1f}")
        return candidates
    
    def _load_article_style_instructions(self) -> str:
        if not self.user_id:
            return ""
        try:
            from pathlib import Path

            base = Path('/root/.openclaw/workspace/content-pipeline/user_memory')
            parts = []

            # 通用：除保险外其他用户共用
            general = base / 'general_non_insurance_article_style.md'
            if self.user_id != 'insurance_agent' and general.exists():
                gt = general.read_text(encoding='utf-8').strip()
                if gt:
                    parts.append(gt)

            # 专用：用户自己的覆盖/补充
            p = base / f"{self.user_id}_article_style.md"
            if p.exists():
                ut = p.read_text(encoding='utf-8').strip()
                if ut:
                    parts.append(ut)

            return "\n\n".join(parts).strip()
        except Exception:
            return ""

    def _build_prompt(self, topic: str, angle: Dict, literature: List[Dict] = None) -> str:
        """构建生成提示词"""

        # 构建文献参考
        refs_text = ""
        if literature:
            refs_text = "\n参考资料（请在文章中适当引用）：\n"
            for i, ref in enumerate(literature[:5], 1):
                refs_text += f"[{i}] {ref.get('title', '')} - {ref.get('source', '')}\n"        
        # 获取写作要求
        content_prefs = self.config.get('content_strategy', {}).get('content_preferences', {})
        tone = ', '.join(content_prefs.get('tone', ['理性', '克制', '有洞见']))
        must_include = ', '.join(content_prefs.get('must_include', ['具体案例', '数据支撑', '可执行建议']))
        
        style_text = ""
        if self._style_instructions:
            style_text = f"\n\n【用户风格记忆（必须遵守）】\n{self._style_instructions}\n"

        title_pref_text = ""
        if self.user_id:
            try:
                from article_library.title_style_manager import load_title_style

                ts = load_title_style(self.user_id)
                if ts and ts.instructions:
                    title_pref_text = f"\n\n【用户标题偏好（通用+专用，必须遵守）】\n{ts.instructions}\n"
            except Exception:
                title_pref_text = ""

        prompt = f"""你是一位资深内容创作者。请以下面的角度撰写一篇关于「{topic}」的文章：

【写作角度】{angle['name']}
【角度说明】{angle['desc']}
【文章基调】{angle['tone']}
【推荐结构】{angle['structure']}

{refs_text}

写作要求：
1. 字数：1500-2000字
2. 基调：{tone}
3. 必须包含：{must_include}
4. 避免：贩卖焦虑、陈词滥调、简单罗列、过度营销
5. 必须从这个特定角度切入，不要写成通用文章
6. 第一行必须是「标题」且只包含标题本身（不要加“标题：”/引号/Markdown加粗）
7. 标题要有吸引力，符合用户标题偏好，并且避免批量同质化（不要都用同一种标点结构，比如不要全是“X：Y”）
{title_pref_text}{style_text}

请直接输出完整文章内容（包含标题）。"""
        
        return prompt
    
    def _evaluate_quality(self, content: str) -> float:
        """评估文章质量"""
        score = 5.0  # 基础分
        
        # 结构完整性
        if any(kw in content for kw in ['引言', '引言', '开头', '前言']):
            score += 0.5
        if any(kw in content for kw in ['结语', '总结', '结尾', '最后']):
            score += 0.5
        
        # 内容要素
        if '案例' in content or '例如' in content or '比如' in content:
            score += 1.0
        if '%' in content or '数据' in content or '统计' in content:
            score += 1.0
        if any(kw in content for kw in ['建议', '方法', '步骤', '怎么做']):
            score += 1.0
        
        # 深度标志
        if any(kw in content for kw in ['本质', '底层', '逻辑', '原理']):
            score += 0.5
        if any(kw in content for kw in ['思考', '洞察', '发现', '启示']):
            score += 0.5
        
        # 字数
        if len(content) >= 1500:
            score += 0.5
        
        return min(score, 10.0)
    
    def _extract_title(self, content: str, topic: str, angle_name: str) -> str:
        """生成/提取标题。

        - 默认行为：从正文第一行提取（不改变既有逻辑）
        - 对 tech_enthusiast：如果存在标题风格记忆文件，则用 LLM 生成标题
        """
        # tech 走定制标题风格
        if self.user_id:
            try:
                from article_library.title_style_manager import load_title_style

                style = load_title_style(self.user_id)
                if style:
                    prompt = (
                        "你将根据文章内容生成一个标题。\n\n"
                        "【用户标题风格要求】\n"
                        f"{style.instructions}\n\n"
                        "【文章主题】\n"
                        f"{topic}\n\n"
                        "【写作角度】\n"
                        f"{angle_name}\n\n"
                        "【文章内容节选】\n"
                        f"{content[:1200]}\n\n"
                        "请输出一个标题。"
                    )
                    title = self.generator._call_llm(prompt, temperature=0.6).strip()
                    # 简单清理：去掉常见前缀/Markdown
                    title = title.strip().strip('"').strip("'")
                    for prefix in ("标题：", "标题:", "**标题：", "**标题:"):
                        if title.startswith(prefix):
                            title = title[len(prefix):].strip()
                    if title.startswith("**") and title.endswith("**") and len(title) > 4:
                        title = title[2:-2].strip()
                    if 5 <= len(title) <= 80:
                        return title
            except Exception:
                pass

        # 默认：从内容中提取标题
        lines = content.strip().split('\n')

        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 5:
                title = line.lstrip('#').strip()
                if len(title) < 100:
                    return title

        return f"{topic}：{angle_name}视角"
    
    def generate_custom_count(self, topic: str, count: int, 
                              literature: List[Dict] = None) -> List[Dict]:
        """
        根据用户指定数量生成
        
        Args:
            topic: 主题
            count: 用户指定的数量
            literature: 参考资料
        """
        # 限制最大数量
        count = min(count, 10)
        count = max(count, 1)
        
        return self.generate_diverse_candidates(topic, count, literature)


# 便捷函数
def generate_articles(topic: str, count: int = 10, literature: List[Dict] = None) -> List[Dict]:
    """
    便捷函数：生成多样化文章
    
    使用示例:
        candidates = generate_articles("AI学习方法论", count=5)
    """
    generator = DiverseArticleGenerator()
    return generator.generate_custom_count(topic, count, literature)


if __name__ == '__main__':
    # 测试
    print("🧪 测试多样化文章生成器")
    
    gen = DiverseArticleGenerator()
    
    # 生成3篇测试
    candidates = gen.generate_diverse_candidates("AI时代的学习方法论", count=3)
    
    print("\n生成的候选文章：")
    for i, c in enumerate(candidates, 1):
        print(f"\n{i}. {c['title']}")
        print(f"   角度: {c['angle_type']} | 质量: {c['quality_score']:.1f} | 字数: {c['word_count']}")
        print(f"   {c['content'][:100]}...")
    
    print("\n✅ 测试完成")
