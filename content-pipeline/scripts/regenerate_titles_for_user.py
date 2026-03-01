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


def _bigrams(s: str) -> set[str]:
    s = re.sub(r"\s+", "", s or "")
    return {s[i : i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else set()


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _leading_token(t: str) -> str:
    t = (t or '').strip()
    # take up to 4 chars as a crude "prefix token"
    return t[:4]


def generate_title(
    user_id: str,
    topic: str,
    angle: str,
    content: str,
    recent_titles: list[str],
) -> str:
    """Goal-driven title generation without prescribing a single template.

    We ask for multiple options, then pick using a novelty+attractiveness score.
    """

    style = load_title_style(user_id)
    style_text = style.instructions if style else ''

    recent = [t for t in (recent_titles or []) if t]
    recent_text = "\n".join(f"- {t}" for t in recent[:18])

    gen = ContentGenerator()

    # 1) generate candidates
    prompt = (
        "你是一位公众号标题编辑。请为下面这篇文章生成 8 个标题候选。\n\n"
        "目标：\n"
        "- 标题要有吸引力（但不标题党），信息密度高，读完标题能大致知道文章在解决什么问题。\n"
        "- 同一用户的一批标题要更丰富：尽量避开近期标题里重复的开头词、句式、关键词组合。\n"
        "- 不要所有标题都用同一种标点结构（例如不要全是‘X：Y’）。\n\n"
        "输出要求：\n"
        "- 只输出 8 行，每行 1 个标题。不要序号、不要引号、不要 Markdown、不要‘标题：’前缀。\n"
        "- 16-32 个中文字符优先，最长不超过 36。\n\n"
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

    raw = (gen._call_llm(prompt, temperature=0.95) or '').strip()
    cands = []
    for line in raw.splitlines():
        line = _clean_title(line)
        if not line:
            continue
        # drop bullet/numbering just in case
        line = re.sub(r"^[\-\*\d\.\)\s]+", "", line).strip()
        if line and line not in cands:
            cands.append(line)
    cands = cands[:8]
    if not cands:
        return ''

    # 2) attractiveness scoring (soft)
    score_prompt = (
        "你是公众号标题编辑。请给每个标题候选打一个【吸引力】分(0-10)，只看标题本身是否想点开，避免标题党。\n"
        "只输出 JSON 数组，每个元素形如 {\"title\":...,\"score\":...}，按输入顺序返回。\n\n"
        "候选：\n" + "\n".join(cands)
    )

    scores = {t: 5.0 for t in cands}
    try:
        import json

        j = gen._call_llm(score_prompt, temperature=0.2)
        arr = json.loads(j)
        for item in arr:
            t = _clean_title(item.get('title', ''))
            s = float(item.get('score', 5.0))
            if t in scores:
                scores[t] = max(0.0, min(10.0, s))
    except Exception:
        pass

    recent_bigrams = [_bigrams(t) for t in recent[:30]]
    recent_prefixes = {_leading_token(t) for t in recent[:60]}

    def novelty(t: str) -> float:
        bg = _bigrams(t)
        sim = 0.0
        for rbg in recent_bigrams:
            sim = max(sim, _jaccard(bg, rbg))
        nov = 1.0 - sim
        # penalize repeating the same leading token within a user batch
        if _leading_token(t) in recent_prefixes:
            nov -= 0.12
        # penalize too many colon-like titles to avoid uniform "X：Y"
        if '：' in t or ':' in t:
            nov -= 0.08
        return max(0.0, nov)

    best = None
    best_score = -1.0
    for t in cands:
        s = scores.get(t, 5.0)
        n = novelty(t)
        total = 0.62 * (s / 10.0) + 0.38 * n
        if total > best_score:
            best_score = total
            best = t

    return _clean_title(best or cands[0])


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

    con = sqlite3.connect(LIB_DB, timeout=60)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA busy_timeout=60000')
    con.execute('PRAGMA journal_mode=WAL')
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

        for wattempt in range(1, 6):
            try:
                cur.execute('update articles set title=? where article_id=?', (title, aid))
                break
            except sqlite3.OperationalError as e:
                if 'locked' in str(e):
                    time.sleep(0.6 * wattempt)
                    continue
                raise

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
