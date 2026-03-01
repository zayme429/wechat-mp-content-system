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

    def _extract_first_array(text: str) -> str:
        l = text.find('[')
        r = text.rfind(']')
        if l != -1 and r != -1 and r > l:
            return text[l : r + 1]
        return text

    # 1) first attempt
    raw = (gen._call_llm(prompt, temperature=0.2) or '').strip()
    out = _parse_json_array(raw) or _parse_json_array(_extract_first_array(raw))

    # 2) repair attempt (ask the model to output ONLY a JSON array)
    if not out and raw:
        repair_prompt = f"""你刚才的输出无法被 JSON 解析。

请你只输出一个 JSON 数组（不要 Markdown，不要解释），元素是字符串，最多 {max_queries} 条。

原始 prompt：
{search_prompt}

你上一次的输出：
{raw}
"""
        raw2 = (gen._call_llm(repair_prompt, temperature=0.0) or '').strip()
        out = _parse_json_array(raw2) or _parse_json_array(_extract_first_array(raw2))

    # 3) generic fallback (avoid hard-coded rules): derive queries from prompt bullets/lines
    if not out:
        lines: List[str] = []
        for ln in (search_prompt or '').splitlines():
            s = ln.strip()
            if not s:
                continue
            if s.startswith('#'):
                continue
            if s.startswith('-'):
                s = s.lstrip('-').strip()
            # drop meta instruction-like lines
            if s.startswith('你是') or s.startswith('请') or s.startswith('输出') or s.startswith('Persona'):
                continue
            lines.append(s)

        # pick a few distinct short phrases
        for s in lines:
            s2 = s.replace('：', ' ').replace(':', ' ').strip()
            if not s2:
                continue
            s2 = s2[:40]
            if s2 and s2 not in out:
                out.append(s2)
            if len(out) >= max_queries:
                break

    return out[:max_queries]
