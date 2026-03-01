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
from content_discovery.query_planner import plan_queries


DEFAULT_PROMPT_FILES = {
    'tech_enthusiast': '/root/.openclaw/workspace/content-pipeline/user_memory/tech_enthusiast_search_prompt.md',
    'jp_music_fan': '/root/.openclaw/workspace/content-pipeline/user_memory/jp_music_fan_search_prompt.md',
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--persona', required=True)
    ap.add_argument('--query', action='append', default=[])
    ap.add_argument('--prompt-file', default='')
    ap.add_argument('--max-results', type=int, default=6)
    ap.add_argument('--db-path', default=DEFAULT_DB_PATH)
    ap.add_argument('--sleep', type=float, default=0.8)
    args = ap.parse_args()

    persona = args.persona

    prompt_file = args.prompt_file or DEFAULT_PROMPT_FILES.get(persona, '')
    search_prompt = ''
    if prompt_file:
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                search_prompt = f.read().strip()
        except Exception:
            search_prompt = ''

    queries = args.query
    if not queries:
        if not search_prompt:
            raise SystemExit('No queries provided and search prompt file missing/empty')
        queries = plan_queries(persona, search_prompt, max_queries=6)

    if not queries:
        raise SystemExit('Failed to plan queries from prompt')

    if not os.environ.get('TAVILY_API_KEY'):
        raise SystemExit('Missing TAVILY_API_KEY in environment')

    total = 0
    print('RUN_START', 'persona='+persona, 'queries='+str(len(queries)), 'max_results='+str(args.max_results), flush=True)
    for qi, q in enumerate(queries, 1):
        print('QUERY_START', f'{qi}/{len(queries)}', q, flush=True)
        results = tavily_search(q, max_results=args.max_results)
        print('QUERY_RESULTS', f'{qi}/{len(queries)}', 'returned='+str(len(results)), flush=True)
        for idx, r in enumerate(results, 1):
            title = (r.get('title') or '').strip()
            url = (r.get('url') or '').strip()
            snippet = (r.get('content') or '').strip()
            if not title:
                continue

            heat = estimate_heat(r, rank=idx)
            fit = analyze_fit(persona, title=title, snippet=snippet, url=url)

            run_id = os.environ.get('DISCOVERY_RUN_ID')

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
                'quality_score': fit.get('quality_score', 0),
                'run_id': run_id,
                'tags': fit.get('tags') or [],
                'fetched_at': now_ts(),
            }

            upsert_candidate(args.db_path, cand)
            total += 1
            print('ITEM', f'{qi}/{len(queries)}', f'{idx}/{len(results)}', 'UPSERT', persona, fit['fit_score'], fit.get('quality_score', 0), int(heat['heat_score']), title[:60], flush=True)
            time.sleep(max(0.0, args.sleep))

        print('QUERY_DONE', f'{qi}/{len(queries)}', q, flush=True)

    print('RUN_DONE', 'total='+str(total), 'db='+args.db_path, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
