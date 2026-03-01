#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')

from content_discovery.collector import estimate_heat, now_ts, tavily_search
from content_discovery.analyzer import analyze_fit
from content_discovery.discovery_store import DEFAULT_DB_PATH, upsert_candidate


DEFAULT_QUERIES = {
    'tech_enthusiast': [
        'AI 工具链 实战 复盘',
        '大模型 工程化 踩坑 复盘',
        'RAG 落地 评估 指标 复盘',
        '性能 优化 成本 延迟 复盘',
        'Agent 工程 实战 工具链',
    ],
    'jp_music_fan': [
        'J-POP 高燃 日本摇滚 歌单 推荐',
        '日摇 现场 ライブ 体验 推荐',
        '动漫 OP ED J-POP 推荐 歌单',
        '日本摇滚 乐队 入坑 指南',
        '甜嗓 高燃 副歌 日本摇滚 推荐',
    ],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--persona', required=True)
    ap.add_argument('--query', action='append', default=[])
    ap.add_argument('--max-results', type=int, default=6)
    ap.add_argument('--db-path', default=DEFAULT_DB_PATH)
    ap.add_argument('--sleep', type=float, default=0.8)
    args = ap.parse_args()

    persona = args.persona
    queries = args.query or DEFAULT_QUERIES.get(persona, [])
    if not queries:
        raise SystemExit('No queries provided and no defaults for persona')

    if not os.environ.get('TAVILY_API_KEY'):
        raise SystemExit('Missing TAVILY_API_KEY in environment')

    total = 0
    for q in queries:
        results = tavily_search(q, max_results=args.max_results)
        for idx, r in enumerate(results, 1):
            title = (r.get('title') or '').strip()
            url = (r.get('url') or '').strip()
            snippet = (r.get('content') or '').strip()
            if not title:
                continue

            heat = estimate_heat(r, rank=idx)
            fit = analyze_fit(persona, title=title, snippet=snippet, url=url)

            cand = {
                'persona': persona,
                'query': q,
                'title': title,
                'url': url,
                'source': 'tavily',
                'author': '',
                'published_at': '',
                'snippet': snippet,
                'heat_score': heat['heat_score'],
                'heat_evidence': heat['heat_evidence'],
                'fit_score': fit['fit_score'],
                'fit_evidence': fit['fit_evidence'],
                'tags': fit.get('tags') or [],
                'fetched_at': now_ts(),
            }

            upsert_candidate(args.db_path, cand)
            total += 1
            print('UPSERT', persona, fit['fit_score'], int(heat['heat_score']), title[:60])
            time.sleep(max(0.0, args.sleep))

    print('DONE total', total, 'db', args.db_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
