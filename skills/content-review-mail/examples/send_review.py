#!/usr/bin/env python3
"""
示例：发送审核邮件
"""

import sys
sys.path.insert(0, '../..')

from scripts.content_review_mail import ContentReviewMail

# 初始化
crm = ContentReviewMail()

# 准备示例候选
candidates = [
    {
        'topic': 'Agentic Workflows时代：程序员的核心竞争力正从"写代码"转向"造规则"',
        'angle_type': '实战派',
        'quality_score': 8.5,
        'uniqueness_score': 7.5,
        'word_count': 1500,
        'content': '''## 引言

凌晨两点，某金融科技团队的架构师李然没有敲击键盘，而是在白板上绘制一张复杂的决策树...

## 现象：从副驾驶到代理人的范式跃迁

GitHub Universe 2024披露的数据显示...

## 深度分析：三层能力的重构

**第一层：问题边界的精细化定义**
...

## 行动建议：构建新技能栈

1. 掌握规约语言与约束设计
2. 深入领域工程而非框架堆砌
...
'''
    },
    {
        'topic': 'AI时代的学习革命：从被动接受到主动构建',
        'angle_type': '深度派',
        'quality_score': 7.8,
        'uniqueness_score': 8.2,
        'word_count': 1800,
        'content': '''## 引言

当知识获取成本趋近于零，学习的本质正在发生根本性改变...

## 现象：AI打破传统学习曲线

过去需要3年掌握的技能，现在可能只需要3个月...

## 深度分析：认知重构的三重维度

**维度一：从记忆到检索**
...

## 行动建议：构建个人AI学习系统

1. 建立问题驱动的学习框架
2. 培养与AI协作的思维模式
...
'''
    }
]

# 发送审核邮件
success = crm.send_review_email(
    to='your-email@example.com',  # 替换为你的邮箱
    subject='📄 内容审核 - 20260226 (2个候选)',
    candidates=candidates,
    article_date='20260226'
)

if success:
    print("✅ 审核邮件已发送")
else:
    print("❌ 发送失败")
