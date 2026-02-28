#!/usr/bin/env python3
"""
保险行业文章生成器
面向保险代理人，专注客户经营和获客
"""

import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')
sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline/src')

from generator.content_generator import ContentGenerator
from article_library.title_generator import InsuranceTitleGenerator

class InsuranceArticleGenerator:
    """保险行业文章生成器"""
    
    # 保险专用10个写作角度
    ANGLES = [
        {
            'name': '故事案例派',
            'desc': '用真实客户案例带出观点，让读者有代入感',
            'tone': '温暖、真实',
            'focus': '客户故事',
            'example': '讲述一个客户从拒绝到信任的过程'
        },
        {
            'name': '话术实战派',
            'desc': '给保险代理人可直接使用的沟通话术和脚本',
            'tone': '直接、实用',
            'focus': '话术模板',
            'example': '客户说"我没钱"时的应对话术'
        },
        {
            'name': '情感连接派',
            'desc': '强调与客户建立情感连接，维护长期关系',
            'tone': '真诚、共情',
            'focus': '关系维护',
            'example': '如何在节日给客户发消息而不像推销'
        },
        {
            'name': '问题解决派',
            'desc': '针对保险代理人的具体工作痛点给出解决方案',
            'tone': '务实、解决导向',
            'focus': '痛点解决',
            'example': '客户不回消息怎么办'
        },
        {
            'name': '观念教育派',
            'desc': '教育客户保险意识，让客户主动思考保障需求',
            'tone': '引导、启发',
            'focus': '观念引导',
            'example': '为什么每个家庭都需要基础保障'
        },
        {
            'name': '转介绍技巧派',
            'desc': '让老客户愿意介绍新客户的方法和时机',
            'tone': '策略、技巧',
            'focus': '转介绍',
            'example': '什么时候开口要转介绍最合适'
        },
        {
            'name': '社群经营派',
            'desc': '微信群、朋友圈的经营方法，打造个人IP',
            'tone': '接地气、实用',
            'focus': '线上运营',
            'example': '朋友圈发什么内容不会被屏蔽'
        },
        {
            'name': '缘故激活派',
            'desc': '激活身边亲戚朋友这些缘故客户的方法',
            'tone': '自然、不尴尬',
            'focus': '缘故市场',
            'example': '如何跟亲戚聊保险而不伤感情'
        },
        {
            'name': '服务差异化派',
            'desc': '用差异化服务赢得客户，建立竞争壁垒',
            'tone': '专业、贴心',
            'focus': '服务升级',
            'example': '保单整理服务让客户主动转介绍'
        },
        {
            'name': '长期主义派',
            'desc': '强调保险是长期事业，需要持续经营',
            'tone': '深度、格局',
            'focus': '职业发展',
            'example': '为什么不要只盯着眼前业绩'
        }
    ]
    
    def __init__(self):
        self.generator = ContentGenerator()
    
    def generate_insurance_articles(self, topic: str, count: int = 10) -> List[Dict]:
        """
        生成保险行业文章
        
        Args:
            topic: 主题（保险客户经营 / 保险获客）
            count: 生成数量（1-10）
        
        Returns:
            文章列表
        """
        print(f"\n🎯 生成保险主题文章：{topic}")
        print(f"   目标受众：保险代理人")
        print(f"   生成数量：{count}篇\n")
        
        candidates = []
        selected_angles = self.ANGLES[:count]
        
        for i, angle in enumerate(selected_angles, 1):
            print(f"  生成第{i}篇：{angle['name']}风格")
            
            # 构建保险专用提示词
            prompt = self._build_insurance_prompt(topic, angle)
            
            # 生成文章
            content = self.generator._call_llm(prompt)
            
            # 评估质量
            quality_score = self._evaluate_insurance_content(content)
            
            # 使用标题生成器生成有吸引力的标题
            title = InsuranceTitleGenerator.generate_title(topic, angle['name'])
            
            candidates.append({
                'title': title,
                'topic': topic,
                'angle': angle['desc'],
                'angle_type': angle['name'],
                'content': content,
                'quality_score': quality_score,
                'word_count': len(content),
                'focus': angle['focus']
            })
            
            print(f"    ✓ 完成，质量分：{quality_score:.1f}")
        
        # 按质量分排序
        candidates.sort(key=lambda x: x['quality_score'], reverse=True)
        
        print(f"\n✅ 生成完成，平均质量分：{sum(c['quality_score'] for c in candidates)/len(candidates):.1f}")
        return candidates
    
    def _build_insurance_prompt(self, topic: str, angle: Dict) -> str:
        """构建保险专用提示词"""
        
        # 确定受众
        if '客户经营' in topic:
            audience = "保险客户（投保人）"
            purpose = "提高客户与代理人的紧密度，加强联系，促进转化"
        else:  # 获客
            audience = "保险代理人（保险业务员）"
            purpose = "帮助代理人获取新客户"
        
        prompt = f"""你是一位资深保险行业内容创作者。

【写作任务】
主题：{topic}
角度：{angle['name']} - {angle['desc']}
目标受众：{audience}
写作目的：{purpose}

【写作风格】
- 基调：{angle['tone']}
- 重点：{angle['focus']}
- 参考：{angle['example']}

【重要要求】
1. 字数：1200-1800字
2. 避免技术术语（如：数字化、SaaS、CRM、私域流量等）
3. 使用保险行业通俗用语（如：跟进、回访、约访、促成、缘故客户等）
4. 必须包含：
   - 具体案例或场景
   - 可直接使用的话术或方法
   - 清晰的步骤或要点
5. 语言风格：接地气、像有经验的保险代理人在分享经验
6. 不要在文章开头写标题，直接写正文内容

【内容结构】
- 开头：场景引入或问题抛出
- 中间：案例分析 + 方法讲解 + 话术示范
- 结尾：总结要点 + 行动建议

请直接输出文章内容（不要标题）。"""
        
        return prompt
    
    def _evaluate_insurance_content(self, content: str) -> float:
        """评估保险文章内容质量"""
        score = 5.0  # 基础分
        
        # 案例/故事
        if any(kw in content for kw in ['客户', '案例', '故事', '比如', '举个例子']):
            score += 1.5
        
        # 话术/方法
        if any(kw in content for kw in ['话术', '可以说', '你可以这样', '建议说', '模板']):
            score += 1.5
        
        # 实用性指标
        if any(kw in content for kw in ['第一步', '第二步', '首先', '然后', '最后']):
            score += 1.0
        
        # 保险专业度
        if any(kw in content for kw in ['保单', '保障', '理赔', '代理人', '客户']):
            score += 0.5
        
        # 字数
        if len(content) >= 1200:
            score += 0.5
        
        return min(score, 10.0)
    
# 便捷函数
def generate_insurance_articles(topic: str, count: int = 10) -> List[Dict]:
    """
    生成保险行业文章
    
    使用示例:
        articles = generate_insurance_articles("保险客户经营", count=5)
    """
    generator = InsuranceArticleGenerator()
    return generator.generate_insurance_articles(topic, count)


if __name__ == '__main__':
    # 测试
    print("🧪 测试保险文章生成器")
    
    gen = InsuranceArticleGenerator()
    
    # 测试生成3篇
    candidates = gen.generate_insurance_articles("保险客户经营", count=3)
    
    print("\n生成的候选文章：")
    for i, c in enumerate(candidates, 1):
        print(f"\n{i}. {c['title']}")
        print(f"   角度: {c['angle_type']} | 质量: {c['quality_score']:.1f}")
        print(f"   前100字: {c['content'][:100]}...")
    
    print("\n✅ 测试完成")
