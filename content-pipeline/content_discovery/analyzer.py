#!/usr/bin/env python3

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from src.generator.content_generator import ContentGenerator


def analyze_fit(persona: str, title: str, snippet: str, url: str = '') -> Dict[str, Any]:
    """LLM-based fit scoring. Returns fit_score 0-100 + evidence."""

    gen = ContentGenerator()

    persona_desc = {
        'jp_music_fan': (
            '年轻、二次元浓度高，沉迷J-POP；偏好甜美/激情的日本摇滚（热血、高燃、现场感）。'
            '喜欢安利/歌单/乐评风格，讲副歌/编曲/鼓点/吉他/情绪推进。'
        ),
        'tech_enthusiast': (
            '专业能力强、技术迷，反感虚有其表；偏好有实在内容、边界条件、取舍代价、复盘对比、可执行细节的文章。'
        ),
    }.get(persona, persona)

    prompt = f"""你是内容选题分析师。请判断下面这篇内容是否适合目标用户（persona），并给出可解释的评分。

persona：{persona}
persona描述：{persona_desc}

候选文章信息：
- 标题：{title}
- 摘要/片段：{snippet}
- 链接：{url}

要求：
1) 输出必须是 JSON（不要 Markdown）
2) 字段：
   - fit_score: 0-100 的整数（是不是这个 persona 会喜欢）
   - quality_score: 0-100 的整数（只看信息密度/可读性/具体性，不看是否喜欢）
   - like_prob: 0-1 小数
   - reasons: 3-6条，具体而非空话
   - evidence: 从标题/摘要中摘取 2-4 个短语作为证据（必须来自给定文本）
   - tags: 3-8 个标签（例如：复盘/踩坑/歌单/安利/现场感/数据/边界条件/空泛 等）
3) 严格：如果信息不足，fit_score 不要给太高，写清楚不足点。
"""

    raw = (gen._call_llm(prompt, temperature=0.2) or '').strip()
    try:
        j = json.loads(raw)
        fit = int(max(0, min(100, int(j.get('fit_score', 0)))))
        quality = int(max(0, min(100, int(j.get('quality_score', 0)))))
        like_prob = float(j.get('like_prob', 0.0))
        return {
            'fit_score': fit,
            'quality_score': quality,
            'fit_evidence': json.dumps(
                {
                    'reasons': j.get('reasons', []),
                    'evidence': j.get('evidence', []),
                    'tags': j.get('tags', []),
                    'like_prob': like_prob,
                    'quality_score': quality,
                },
                ensure_ascii=False,
            ),
            'tags': j.get('tags', []),
        }
    except Exception:
        # conservative fallback
        return {
            'fit_score': 0,
            'quality_score': 0,
            'fit_evidence': json.dumps({'raw': raw[:800]}, ensure_ascii=False),
            'tags': [],
        }
