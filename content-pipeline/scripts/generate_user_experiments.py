#!/usr/bin/env python3
"""Generate experimental articles for multiple users.

This script is intentionally simple: it uses SmartArticleService to generate and
save candidates, and associates saved articles to the given user.

Usage:
  KIMI_API_KEY=... python3 scripts/generate_user_experiments.py --user tech_enthusiast --topic "AI工具链" --batches 3

Notes:
- Each batch generates up to 10 candidates (SmartArticleService limit).
- No push to WeChat draft box.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime

sys.path.append('/root/.openclaw/workspace/content-pipeline')

from article_library.smart_service import SmartArticleService


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--user', required=True)
    ap.add_argument('--topic', required=True)
    ap.add_argument('--batches', type=int, default=3)
    ap.add_argument('--sleep', type=float, default=0.0)
    ap.add_argument('--out', default='')
    args = ap.parse_args()

    out_path = args.out or f"/root/.openclaw/workspace/content-pipeline/experiment_{args.user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    svc = SmartArticleService()

    total_saved = 0
    with open(out_path, 'w', encoding='utf-8') as f:
        for i in range(1, args.batches + 1):
            payload = {
                'batch': i,
                'user_id': args.user,
                'topic': args.topic,
                'ts': datetime.now().isoformat(),
            }
            try:
                res = svc.handle_request(args.topic, force_generate=True, user_id=args.user)
                payload['success'] = bool(res.get('success'))
                payload['source'] = res.get('source')
                payload['message'] = res.get('message')
                art = res.get('article') or {}
                payload['article'] = {
                    'article_id': art.get('article_id'),
                    'title': art.get('title'),
                }
                payload['alternatives_count'] = len(res.get('alternatives') or [])
                if payload['success']:
                    # SmartArticleService saves 10 candidates; the returned 'article' is one of them.
                    total_saved += 10
            except Exception as e:
                payload['success'] = False
                payload['error'] = str(e)

            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            f.flush()

            if args.sleep:
                time.sleep(args.sleep)

    print(f"DONE user={args.user} batches={args.batches} approx_saved={total_saved} out={out_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
