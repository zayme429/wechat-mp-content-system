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
import re
import sqlite3
import sys
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


def generate_title(user_id: str, topic: str, angle: str, content: str) -> str:
    style = load_title_style(user_id)
    style_text = style.instructions if style else ''

    prompt = (
        "你将为一篇文章生成一个公众号标题。\n"
        "硬性要求：\n"
        "- 只输出标题本身（不要加\"标题：\"前缀，不要引号，不要Markdown加粗）。\n"
        "- 16-32个中文字符优先，最长不超过36个中文字符。\n"
        "- 要有吸引力，但不要标题党。\n\n"
        "【用户标题偏好（通用+专用，必须遵守）】\n"
        f"{style_text}\n\n"
        "【主题】\n"
        f"{topic}\n\n"
        "【角度】\n"
        f"{angle or ''}\n\n"
        "【正文节选】\n"
        f"{(content or '')[:1400]}\n"
    )

    gen = ContentGenerator()
    t = gen._call_llm(prompt, temperature=0.7)
    return _clean_title(t)


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

        title = generate_title(user_id, row['topic'], row['angle'], row['content'])
        if not title:
            print('SKIP empty title', aid)
            continue

        cur.execute('update articles set title=? where article_id=?', (title, aid))
        update_markdown_title(row['file_path'], title)
        updated += 1
        print('UPDATED', aid, 'user', user_id, '->', title)

    con.commit()
    con.close()
    up.close()

    print('DONE updated', updated)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
