#!/usr/bin/env python3

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from src.generator.content_generator import ContentGenerator

from content_discovery.discovery_store import (
    DEFAULT_DB_PATH,
    connect,
    init_db,
    list_candidates,
)


def _persona_desc(persona: str) -> str:
    if persona == 'jp_music_fan':
        return (
            '年轻、二次元浓度高，沉迷J-POP；偏好甜美/激情的日本摇滚（热血、高燃、现场感）。'
            '喜欢安利/歌单/乐评风格，讲副歌/编曲/鼓点/吉他/情绪推进。'
        )
    if persona == 'tech_enthusiast':
        return '专业能力强、技术迷，反感虚有其表；偏好有实在内容、边界条件、取舍代价、复盘对比、可执行细节的文章。'
    return persona


def upsert_conclusion(
    persona: str,
    conclusion_text: str,
    evidence: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    init_db(db_path)
    with connect(db_path) as con:
        con.execute(
            """
            INSERT INTO persona_conclusions(persona, conclusion_text, evidence_json, generated_at)
            VALUES(?,?,?,?)
            ON CONFLICT(persona) DO UPDATE SET
              conclusion_text=excluded.conclusion_text,
              evidence_json=excluded.evidence_json,
              generated_at=excluded.generated_at
            """,
            (
                persona,
                (conclusion_text or '').strip(),
                json.dumps(evidence or {}, ensure_ascii=False),
                int(time.time()),
            ),
        )


def get_conclusion(persona: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    with connect(db_path) as con:
        row = con.execute(
            'SELECT persona, conclusion_text, evidence_json, generated_at FROM persona_conclusions WHERE persona=?',
            (persona,),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d['evidence'] = json.loads(d.get('evidence_json') or '{}')
    except Exception:
        d['evidence'] = {}
    return d


def generate_conclusion(
    persona: str,
    db_path: str = DEFAULT_DB_PATH,
    top_k: int = 20,
) -> Dict[str, Any]:
    """Generate a short, actionable writing conclusion for a persona.

    Uses the top candidates by heat*fit from discovery db.
    """

    items = list_candidates(db_path, persona=persona, limit=max(50, top_k))
    items = [it for it in items if it.get('title')]
    items = items[:top_k]

    # Build compact evidence pack
    lines: List[str] = []
    used = 0
    for it in items:
        title = (it.get('title') or '').strip()
        snippet = (it.get('snippet') or '').strip()
        heat = it.get('heat_score')
        fit = it.get('fit_score')
        url = it.get('url') or ''
        lines.append(f"- title={title} | heat={heat} fit={fit} | url={url}")
        if snippet:
            lines.append(f"  snippet={snippet[:180]}")
        used += 1

    evidence_text = '\n'.join(lines)

    gen = ContentGenerator()
    prompt = f"""你是内容策略分析师。

我们为 persona={persona} 收集了一批高热度/高匹配的文章候选。请你基于这些候选，输出对“未来如何写这个 persona 的文章”的结论。

persona描述：{_persona_desc(persona)}

候选证据（标题+摘要，按综合排序）：
{evidence_text}

输出要求（必须严格按此结构，纯文本，不要 Markdown）：
1) 三条选题结论：每条一句话（必须可执行）
2) 三条标题结论：每条一句话（必须可执行；强调避免同质化）
3) 三条正文结构结论：每条一句话（必须可执行）
4) 禁忌清单：3-6条（避免写成什么样）

注意：不要虚话套话，必须从这些候选“归纳”出写法倾向。
"""

    text = (gen._call_llm(prompt, temperature=0.2) or '').strip()

    evidence = {
        'top_k': used,
        'items': [
            {
                'title': it.get('title'),
                'url': it.get('url'),
                'heat_score': it.get('heat_score'),
                'fit_score': it.get('fit_score'),
            }
            for it in items
        ],
    }

    upsert_conclusion(persona, text, evidence, db_path=db_path)
    return {'persona': persona, 'conclusion_text': text, 'evidence': evidence}
