#!/usr/bin/env python3

from __future__ import annotations

import json
from typing import Any, Dict, List

from src.generator.content_generator import ContentGenerator


def plan_queries(persona: str, search_prompt: str, max_queries: int = 6) -> List[str]:
    """Turn a free-form search prompt into multiple search queries."""

    gen = ContentGenerator()

    prompt = f"""你是搜索策略规划器。我们要为 persona={persona} 做内容采集。

用户提供的搜索意图（prompt）：
{search_prompt}

请你输出一个 JSON 数组（不要 Markdown），数组元素是字符串，每个字符串是一条可以用于搜索引擎/站内搜索的查询关键词组合。

要求：
- 至少 5 条，最多 {max_queries} 条
- 需要覆盖不同角度、不同表达（不要同义改写）
- 每条尽量短（8-20 个中文字符为主），用空格分隔关键字也可以
- 要有“内容类型”提示词（例如：复盘/歌单/乐评/入坑/现场/踩坑/评估/对比/实战 等），而不是纯主题词

只输出 JSON 数组。
"""

    raw = (gen._call_llm(prompt, temperature=0.2) or '').strip()

    def _parse_json_array(text: str) -> List[str]:
        try:
            arr = json.loads(text)
        except Exception:
            return []
        if not isinstance(arr, list):
            return []
        out: List[str] = []
        for x in arr:
            if isinstance(x, str):
                s = x.strip()
                if s and s not in out:
                    out.append(s)
        return out

    # 1) strict parse
    out = _parse_json_array(raw)

    # 2) try to extract the first JSON array substring
    if not out:
        l = raw.find('[')
        r = raw.rfind(']')
        if l != -1 and r != -1 and r > l:
            out = _parse_json_array(raw[l : r + 1])

    # 3) fallback: use the prompt itself as one query
    if not out:
        s = (search_prompt or '').strip()
        if s:
            out = [s[:80]]

    return out[:max_queries]
