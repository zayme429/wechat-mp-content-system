#!/usr/bin/env python3
"""Regenerate full articles (title + content) for a given user.

Scope:
- Only non-insurance users.
- Updates existing articles in library.db (title/content/word_count/quality_score).
- Updates markdown file content if file_path exists.

Why:
- Use new persona + style memories to rebuild both title and article body.
- Keep insurance flow untouched.

Usage:
  KIMI_API_KEY=... python3 scripts/regenerate_articles_for_user.py --user-id tech_enthusiast --user-last-n 30
"""

from __future__ import annotations

import argparse
import random
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.append('/root/.openclaw/workspace/content-pipeline')

from article_library.diverse_generator import DiverseArticleGenerator


LIB_DB = '/root/.openclaw/workspace/content-pipeline/article_library/library.db'
UP_DB = '/root/.openclaw/workspace/content-pipeline/user_preferences.db'
ART_DIR = Path('/root/.openclaw/workspace/content-pipeline/article_library/articles')


def _clean_title(t: str) -> str:
    t = (t or '').strip().strip('"').strip("'")
    for prefix in ('标题：', '标题:', '**标题：', '**标题:'):
        if t.startswith(prefix):
            t = t[len(prefix):].strip()
    if t.startswith('**') and t.endswith('**') and len(t) > 4:
        t = t[2:-2].strip()
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def extract_title_from_content(content: str) -> str:
    for line in (content or '').splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            line = line.lstrip('#').strip()
        return _clean_title(line)
    return ''


def update_markdown(file_path: str | None, article_id: str, content: str) -> str:
    if file_path:
        p = Path(file_path)
    else:
        p = ART_DIR / f"{article_id}.md"

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text((content or '').rstrip() + '\n', encoding='utf-8')
    return str(p)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--user-id', required=True)
    ap.add_argument('--user-last-n', type=int, default=30)
    ap.add_argument('--sleep', type=float, default=1.2)
    ap.add_argument('--jitter', type=float, default=1.0)
    ap.add_argument('--retries', type=int, default=6)
    args = ap.parse_args()

    if args.user_id == 'insurance_agent':
        raise SystemExit('Refusing to touch insurance_agent')

    # get article ids
    up = sqlite3.connect(UP_DB)
    upcur = up.cursor()
    upcur.execute(
        'select article_id from user_articles where user_id=? order by id desc limit ?',
        (args.user_id, args.user_last_n),
    )
    ids = [r[0] for r in upcur.fetchall()]
    up.close()

    if not ids:
        print('No articles for user', args.user_id)
        return 0

    con = sqlite3.connect(LIB_DB, timeout=60)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA busy_timeout=60000')
    con.execute('PRAGMA journal_mode=WAL')
    cur = con.cursor()

    q = 'select article_id,topic,angle_type,angle,content,file_path from articles where article_id in (%s)' % (','.join('?' * len(ids)))
    cur.execute(q, ids)
    rows = cur.fetchall()
    by_id = {r['article_id']: r for r in rows}

    gen = DiverseArticleGenerator(user_id=args.user_id)

    updated = 0
    for aid in ids:
        row = by_id.get(aid)
        if not row:
            print('SKIP missing article', aid)
            continue

        # pick angle definition: match by name else default
        angle_def = None
        if row['angle_type']:
            for a in gen.ANGLES:
                if a.get('name') == row['angle_type']:
                    angle_def = a
                    break
        if not angle_def:
            angle_def = gen.ANGLES[0]

        prompt = gen._build_prompt(row['topic'], angle_def, literature=None)

        content = ''
        for attempt in range(1, args.retries + 1):
            try:
                content = gen.generator._call_llm(prompt, temperature=0.85)
                break
            except Exception as e:
                msg = str(e)
                print('ERROR gen', aid, f'attempt={attempt}', msg)
                if 'overloaded' in msg or '429' in msg or 'timeout' in msg.lower():
                    time.sleep(min(30.0, 2.0 ** attempt) + random.random())
                    continue
                break

        if not content:
            print('SKIP empty content', aid)
            continue

        title = extract_title_from_content(content)
        if not title:
            title = row['topic']

        quality = gen._evaluate_quality(content)
        wc = len(content)

        # update DB with retry on locks
        for wattempt in range(1, 6):
            try:
                file_path = update_markdown(row['file_path'], aid, content)
                cur.execute(
                    'update articles set title=?, content=?, word_count=?, quality_score=?, angle=?, angle_type=?, file_path=? where article_id=?',
                    (title, content, wc, quality, angle_def.get('desc'), angle_def.get('name'), file_path, aid),
                )
                break
            except sqlite3.OperationalError as e:
                if 'locked' in str(e):
                    time.sleep(0.6 * wattempt)
                    continue
                raise

        updated += 1
        print('UPDATED', aid, '->', title)

        time.sleep(max(0.0, args.sleep + random.random() * max(0.0, args.jitter)))

    con.commit()
    con.close()

    print('DONE updated', updated)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
