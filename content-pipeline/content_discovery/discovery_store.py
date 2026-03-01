#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_DB_PATH = os.environ.get(
    'DISCOVERY_DB_PATH',
    '/root/.openclaw/workspace/content-pipeline/content_discovery/discovery.db',
)


def connect(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, timeout=60)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA busy_timeout=60000')
    con.execute('PRAGMA journal_mode=WAL')
    return con


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with connect(db_path) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS content_candidates (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              persona TEXT NOT NULL,
              query TEXT,
              title TEXT NOT NULL,
              url TEXT,
              source TEXT,
              author TEXT,
              published_at TEXT,
              snippet TEXT,
              heat_score REAL,
              heat_evidence TEXT,
              fit_score REAL,
              fit_evidence TEXT,
              quality_score REAL,
              run_id TEXT,
              tags_json TEXT,
              fetched_at INTEGER NOT NULL
            );
            """
        )
        # Forward-compatible schema upgrades (must run before creating indexes on new columns)
        try:
            con.execute('ALTER TABLE content_candidates ADD COLUMN quality_score REAL')
        except Exception:
            pass
        try:
            con.execute('ALTER TABLE content_candidates ADD COLUMN run_id TEXT')
        except Exception:
            pass

        con.execute('CREATE INDEX IF NOT EXISTS idx_candidates_persona ON content_candidates(persona)')
        con.execute('CREATE INDEX IF NOT EXISTS idx_candidates_heat ON content_candidates(heat_score)')
        con.execute('CREATE INDEX IF NOT EXISTS idx_candidates_fit ON content_candidates(fit_score)')
        con.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_candidates_url ON content_candidates(url)')
        con.execute('CREATE INDEX IF NOT EXISTS idx_candidates_run ON content_candidates(run_id)')

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS discovery_runs (
              task_id TEXT PRIMARY KEY,
              persona TEXT NOT NULL,
              planned_queries_json TEXT,
              log_path TEXT,
              status TEXT,
              started_at INTEGER NOT NULL,
              finished_at INTEGER
            );
            """
        )
        con.execute('CREATE INDEX IF NOT EXISTS idx_runs_persona_started ON discovery_runs(persona, started_at)')

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS persona_conclusions (
              persona TEXT PRIMARY KEY,
              conclusion_text TEXT NOT NULL,
              evidence_json TEXT,
              generated_at INTEGER NOT NULL
            );
            """
        )


def upsert_candidate(db_path: str, c: Dict[str, Any]) -> None:
    init_db(db_path)
    fetched_at = int(c.get('fetched_at') or time.time())
    persona = c.get('persona') or ''
    title = c.get('title') or ''
    if not persona or not title:
        raise ValueError('candidate missing persona/title')

    tags_json = None
    if isinstance(c.get('tags'), (list, dict)):
        tags_json = json.dumps(c.get('tags'), ensure_ascii=False)

    with connect(db_path) as con:
        con.execute(
            """
            INSERT INTO content_candidates(
              persona, query, title, url, source, author, published_at, snippet,
              heat_score, heat_evidence, fit_score, fit_evidence, quality_score, run_id, tags_json, fetched_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(url) DO UPDATE SET
              persona=excluded.persona,
              query=excluded.query,
              title=excluded.title,
              source=excluded.source,
              author=excluded.author,
              published_at=excluded.published_at,
              snippet=excluded.snippet,
              heat_score=excluded.heat_score,
              heat_evidence=excluded.heat_evidence,
              fit_score=excluded.fit_score,
              fit_evidence=excluded.fit_evidence,
              quality_score=excluded.quality_score,
              run_id=excluded.run_id,
              tags_json=excluded.tags_json,
              fetched_at=excluded.fetched_at
            """,
            (
                persona,
                c.get('query'),
                title,
                c.get('url'),
                c.get('source'),
                c.get('author'),
                c.get('published_at'),
                c.get('snippet'),
                c.get('heat_score'),
                c.get('heat_evidence'),
                c.get('fit_score'),
                c.get('fit_evidence'),
                c.get('quality_score'),
                c.get('run_id'),
                tags_json,
                fetched_at,
            ),
        )


def import_jsonl(db_path: str, jsonl_text: str) -> Tuple[int, int]:
    init_db(db_path)
    ok = 0
    bad = 0
    for line in (jsonl_text or '').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            c = json.loads(line)
            upsert_candidate(db_path, c)
            ok += 1
        except Exception:
            bad += 1
    return ok, bad


def list_candidates(
    db_path: str,
    persona: Optional[str] = None,
    q: Optional[str] = None,
    min_heat: Optional[float] = None,
    min_fit: Optional[float] = None,
    min_quality: Optional[float] = None,
    run_id: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    init_db(db_path)
    where = ['1=1']
    params: List[Any] = []

    if persona:
        where.append('persona = ?')
        params.append(persona)
    if q:
        where.append('(title LIKE ? OR snippet LIKE ? OR url LIKE ?)')
        params.extend([f'%{q}%', f'%{q}%', f'%{q}%'])
    if min_heat is not None:
        where.append('(heat_score IS NOT NULL AND heat_score >= ?)')
        params.append(float(min_heat))
    if min_fit is not None:
        where.append('(fit_score IS NOT NULL AND fit_score >= ?)')
        params.append(float(min_fit))
    if min_quality is not None:
        where.append('(quality_score IS NOT NULL AND quality_score >= ?)')
        params.append(float(min_quality))
    if run_id:
        where.append('run_id = ?')
        params.append(run_id)

    sql = (
        'SELECT * FROM content_candidates '
        f"WHERE {' AND '.join(where)} "
        'ORDER BY (COALESCE(heat_score,0) * COALESCE(fit_score,0)) DESC, fetched_at DESC '
        'LIMIT ?'
    )
    params.append(int(limit))

    with connect(db_path) as con:
        rows = con.execute(sql, params).fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        # decode tags
        tj = d.get('tags_json')
        if tj:
            try:
                d['tags'] = json.loads(tj)
            except Exception:
                d['tags'] = None
        else:
            d['tags'] = None
        out.append(d)
    return out


def stats(db_path: str) -> Dict[str, Any]:
    init_db(db_path)
    with connect(db_path) as con:
        total = con.execute('SELECT COUNT(*) AS c FROM content_candidates').fetchone()['c']
        by_persona = con.execute(
            'SELECT persona, COUNT(*) AS c FROM content_candidates GROUP BY persona ORDER BY c DESC'
        ).fetchall()
    return {
        'total': total,
        'by_persona': [dict(r) for r in by_persona],
    }
