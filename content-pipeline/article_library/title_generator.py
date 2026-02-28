"""
保险行业文章标题生成器 V4.1
自然流畅、有吸引力的专业标题
"""

import random
from typing import List

class InsuranceTitleGenerator:
    """保险行业文章标题生成器 - V4.1"""
    
    # 自然流畅的标题模板 - 避免套路化表达
    TEMPLATES = [
        # 成果展示型
        "{时间}深耕{客户类型}，我收获了{收获}",
        "从{状态A}到{状态B}，{客户类型}经营的{核心方法}",
        "{客户类型}{结果}，靠的是这{数字}个{细节}",
        "{客户类型}说'{话语}'，我这样{动作}",
        
        # 方法分享型
        "{客户类型}经营：{数字}个{细节}帮你{结果}",
        "{场景}时，{数字}步{动作}{客户类型}",
        "{问题}，{职业}这样{动作}最有效",
        "{客户类型}不{动作}？可能是{关键点}没做好",
        
        # 经验总结型
        "{数字}个{客户类型}让我明白：{核心逻辑}",
        "{时间}{动作}{客户类型}，我总结了这{数字}点",
        "{客户类型}的{关键点}，{职业}必看",
        
        # 对比反思型
        "{错误做法}不如{正确做法}，{客户类型}经营的真相",
        "别人{负面行为}，我{正面行为}，{客户类型}反而{结果}",
        "从{负面状态}到{正面状态}，我的{客户类型}经营之路",
        
        # 场景切入型
        "{场景}后，{客户类型}{结果}的{核心方法}",
        "{场景}时，我这样{动作}{客户类型}",
    ]
    
    # 自然词汇库 - 避免套路化表达
    VOCABULARY = {
        "时间": ["半年", "一年", "两年", "三年", "五年"],
        "客户类型": ["缘故客户", "老客户", "转介绍客户", "沉默客户", "高端客户"],
        "结果": ["主动加保", "持续转介绍", "高度认可", "长期信任"],
        "收获": ["信任", "认可", "友情", "长期合作"],
        "状态A": ["陌生", "犹豫", "观望", "不信任"],
        "状态B": ["信任", "认可", "成交", "深度合作"],
        "核心方法": ["温度服务", "长期主义", "专业致胜", "情感账户", "细节经营"],
        "数字": ["三", "五", "七", "十"],
        "细节": ["小动作", "小细节", "沟通方式", "服务细节"],
        "场景": ["理赔现场", "客户生日", "续费节点", "节日问候"],
        "问题": ["客户不回复", "约访被拒", "续费困难", "转介绍少"],
        "职业": ["保险顾问", "保险代理人", "保险人"],
        "动作": ["跟进", "回访", "经营", "维护", "服务"],
        "关键点": ["情感连接", "专业度", "长期陪伴", "信任感"],
        "核心逻辑": ["服务先于销售", "情感先于业务", "长期价值"],
        "错误做法": ["群发消息", "硬推销", "频繁打扰"],
        "正确做法": ["用心服务", "情感连接", "专业建议"],
        "负面行为": ["推销产品", "群发广告", "催促下单"],
        "正面行为": ["关心生活", "提供专业价值", "长期陪伴"],
        "负面状态": ["业绩低迷", "客户流失", "没有方向"],
        "正面状态": ["业绩稳定", "客户认可", "转介绍不断"],
        "话语": ["我再考虑", "太贵了", "我不需要", "你靠谱"],
    }
    
    @classmethod
    def generate_title(cls, topic: str = "保险客户经营") -> str:
        """生成标题"""
        template = random.choice(cls.TEMPLATES)
        title = cls._fill_template(template)
        return cls._ensure_length(title)
    
    @classmethod
    def _fill_template(cls, template: str) -> str:
        """填充模板变量"""
        import re
        title = template
        for _ in range(20):
            if '{' not in title:
                break
            match = re.search(r'\{([^}]+)\}', title)
            if not match:
                break
            var_name = match.group(1)
            if var_name in cls.VOCABULARY:
                replacement = random.choice(cls.VOCABULARY[var_name])
                title = title[:match.start()] + replacement + title[match.end():]
            else:
                title = title[:match.start()] + title[match.end():]
        return title
    
    @classmethod
    def _ensure_length(cls, title: str, max_bytes: int = 64) -> str:
        """确保标题长度合适"""
        if len(title.encode('utf-8')) <= max_bytes:
            return title
        
        # 重新生成
        for _ in range(10):
            new_title = cls.generate_title()
            if len(new_title.encode('utf-8')) <= max_bytes:
                return new_title
        
        # 截断
        while len(title.encode('utf-8')) > max_bytes - 3:
            title = title[:-1]
        return title + "..."
    
    @classmethod
    def generate_batch(cls, topic: str, count: int = 5) -> List[str]:
        """批量生成标题"""
        titles = []
        for _ in range(count * 2):
            if len(titles) >= count:
                break
            title = cls.generate_title(topic)
            if '{' not in title and title not in titles:
                titles.append(title)
        return titles[:count]


# 便捷函数
def generate_insurance_title(topic: str = "保险客户经营") -> str:
    return InsuranceTitleGenerator.generate_title(topic)


def generate_insurance_titles(topic: str = "保险客户经营", count: int = 5) -> List[str]:
    return InsuranceTitleGenerator.generate_batch(topic, count)


# 测试
if __name__ == '__main__':
    print("🎯 保险标题生成器 V4.1 - 自然流畅\n")
    for i, title in enumerate(generate_insurance_titles("保险客户经营", 10), 1):
        print(f"{i}. {title}")
