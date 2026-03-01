#!/usr/bin/env python3
"""Regenerate titles for given articles using per-user title memories.

Scope:
- Non-insurance users only (insurance_agent untouched).
- Updates library.db articles.title
- Updates markdown file first line if file_path exists

Usage:
  KIMI_API_KEY=... python3 scripts/regenerate_titles_for_user.py --article-id XXX --user-id tech_enthusiast
  KIMI_API_KEY=... python3 scripts/regenerate_titles_for_user.py --revision-needed

Notes:
- Title is generated via ContentGenerator._call_llm using the loaded title style.
"""

from __future__ import annotations

import argparse
import os
import random
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.append('/root/.openclaw/workspace/content-pipeline')

from src.generator.content_generator import ContentGenerator
from article_library.title_style_manager import load_title_style


LIB_DB = '/root/.openclaw/workspace/content-pipeline/article_library/library.db'
UP_DB = '/root/.openclaw/workspace/content-pipeline/user_preferences.db'


def _clean_title(t: str) -> str:
    t = (t or '').strip().strip('"').strip("'")
    for prefix in ("标题：", "标题:", "**标题：", "**标题:"):
        if t.startswith(prefix):
            t = t[len(prefix):].strip()
    if t.startswith('**') and t.endswith('**') and len(t) > 4:
        t = t[2:-2].strip()
    # collapse whitespace
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def generate_title(
    user_id: str,
    topic: str,
    angle: str,
    content: str,
    recent_titles: list[str],
) -> str:
    """Goal-driven title generation (no fixed template).

    Strategy:
    - Ask for 3 candidate titles.
    - Ask for 1 final selection that is both attractive and not too similar to recent titles.
    """

    style = load_title_style(user_id)
    style_text = style.instructions if style else ''

    recent_text = "\n".join(f"- {t}" for t in (recent_titles or [])[:18])

    prompt = (
        "你是一位公众号标题编辑。请为下面这篇文章生成标题。\n\n"
        "目标：\n"
        "- 吸引点击（但不标题党）、信息密度高、读完标题能大致知道文章在解决什么问题。\n"
        "- 让同一用户的一批文章标题整体更丰富：尽量避开近期标题里重复的开头词、重复的句式、重复的关键词组合。\n\n"
        "输出要求：\n"
        "- 先给出 3 个候选标题（每行一个）。\n"
        "- 然后给出 1 个最终标题（单独一行，以 FINAL: 开头）。\n"
        "- 标题只输出标题本身：不要加\"标题：\"前缀，不要引号，不要Markdown。\n"
        "- 标题长度：16-32 个中文字符优先，最长不超过 36。\n\n"
        "【用户标题偏好（通用+专用）】\n"
        f"{style_text}\n\n"
        "【该用户最近已用过的标题（用于避重复）】\n"
        f"{recent_text}\n\n"
        "【主题】\n"
        f"{topic}\n\n"
        "【角度】\n"
        f"{angle or ''}\n\n"
        "【正文节选】\n"
        f"{(content or '')[:1400]}\n"
    )

    gen = ContentGenerator()
    raw = gen._call_llm(prompt, temperature=0.85)
    raw = (raw or '').strip()

    final = ''
    for line in raw.splitlines():
        if line.strip().upper().startswith('FINAL:'):
            final = line.split(':', 1)[1].strip()
            break
    if not final:
        # fallback to last non-empty line
        for line in reversed(raw.splitlines()):
            if line.strip():
                final = line.strip()
                break

    return _clean_title(final)


def update_markdown_title(file_path: str, title: str) -> None:
    if not file_path:
        return
    p = Path(file_path)
    if not p.exists():
        return
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()
    if not lines:
        p.write_text(title + "\n", encoding='utf-8')
        return

    # Replace first non-empty line.
    for i, line in enumerate(lines):
        if line.strip():
            lines[i] = title
            break
    else:
        lines.insert(0, title)

    p.write_text("\n".join(lines) + "\n", encoding='utf-8')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--article-id', action='append', default=[])
    ap.add_argument('--user-id', default='')
    ap.add_argument('--revision-needed', action='store_true')
    ap.add_argument('--user-last-n', type=int, default=0, help='Regenerate titles for last N articles of given --user-id')
    ap.add_argument('--sleep', type=float, default=0.8, help='Base sleep seconds between articles')
    ap.add_argument('--jitter', type=float, default=0.6, help='Random jitter seconds added to sleep')
    ap.add_argument('--retries', type=int, default=5, help='Retries on overloaded/temporary errors')
    args = ap.parse_args()

    if args.user_id == 'insurance_agent':
        raise SystemExit('Refusing to touch insurance_agent')

    con = sqlite3.connect(LIB_DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA busy_timeout=30000')
    cur = con.cursor()

    targets = []
    if args.revision_needed:
        cur.execute("select article_id,topic,angle,content,file_path from articles where status='reviewed_revision_needed'")
        targets = cur.fetchall()
    elif args.user_last_n and args.user_id:
        up = sqlite3.connect(UP_DB)
        upcur = up.cursor()
        upcur.execute(
            'select article_id from user_articles where user_id=? order by id desc limit ?',
            (args.user_id, args.user_last_n),
        )
        ids = [r[0] for r in upcur.fetchall()]
        up.close()
        if ids:
            q = 'select article_id,topic,angle,content,file_path from articles where article_id in (%s)' % (','.join('?'*len(ids)))
            cur.execute(q, ids)
            targets = cur.fetchall()
    elif args.article_id:
        q = 'select article_id,topic,angle,content,file_path from articles where article_id in (%s)' % (','.join('?'*len(args.article_id)))
        cur.execute(q, args.article_id)
        targets = cur.fetchall()

    if not targets:
        print('No targets')
        return 0

    # lookup user_id per article if not provided
    up = sqlite3.connect(UP_DB)
    upcur = up.cursor()

    updated = 0
    for row in targets:
        aid = row['article_id']
        user_id = args.user_id
        if not user_id:
            upcur.execute('select user_id from user_articles where article_id=?', (aid,))
            r = upcur.fetchone()
            user_id = r[0] if r else ''

        if not user_id:
            print('SKIP no user_id for', aid)
            continue
        if user_id == 'insurance_agent':
            print('SKIP insurance_agent', aid)
            continue

        # collect some recent titles for diversity constraint
        upcur.execute('select article_id from user_articles where user_id=? order by id desc limit 60', (user_id,))
        recent_ids = [r[0] for r in upcur.fetchall()]
        recent_titles = []
        if recent_ids:
            q2 = 'select title from articles where article_id in (%s)' % (','.join('?'*len(recent_ids)))
            cur.execute(q2, recent_ids)
            recent_titles = [(_clean_title(r[0]) if r and r[0] else '') for r in cur.fetchall()]
            recent_titles = [t for t in recent_titles if t]

        title = ''
        for attempt in range(1, args.retries + 1):
            try:
                title = generate_title(user_id, row['topic'], row['angle'], row['content'], recent_titles)
                break
            except Exception as e:
                msg = str(e)
                print('ERROR title generation', aid, 'user', user_id, f'attempt={attempt}', msg)
                # simple backoff for temporary overloads
                if 'overloaded' in msg or '429' in msg or 'timeout' in msg.lower():
                    time.sleep(min(20.0, 2.0 ** attempt) + random.random())
                    continue
                break

        if not title:
            print('SKIP empty title', aid)
            continue

        cur.execute('update articles set title=? where article_id=?', (title, aid))
        update_markdown_title(row['file_path'], title)
        updated += 1
        print('UPDATED', aid, 'user', user_id, '->', title)

        # reduce provider load
        if args.sleep or args.jitter:
            time.sleep(max(0.0, args.sleep + random.random() * max(0.0, args.jitter)))

    con.commit()
    con.close()
    up.close()

    print('DONE updated', updated)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
