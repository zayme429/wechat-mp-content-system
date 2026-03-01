#!/usr/bin/env python3

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from content_discovery.discovery_store import DEFAULT_DB_PATH, connect, init_db


def start_run(
    task_id: str,
    persona: str,
    planned_queries: List[str],
    log_path: str,
    pid: int | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    init_db(db_path)
    with connect(db_path) as con:
        con.execute(
            """
            INSERT INTO discovery_runs(task_id, persona, planned_queries_json, log_path, status, pid, started_at, finished_at)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(task_id) DO UPDATE SET
              persona=excluded.persona,
              planned_queries_json=excluded.planned_queries_json,
              log_path=excluded.log_path,
              status=excluded.status,
              pid=excluded.pid,
              started_at=excluded.started_at,
              finished_at=excluded.finished_at
            """,
            (
                task_id,
                persona,
                json.dumps(planned_queries or [], ensure_ascii=False),
                log_path,
                'running',
                int(pid) if pid else None,
                int(time.time()),
                None,
            ),
        )


def finish_run(task_id: str, status: str = 'finished', db_path: str = DEFAULT_DB_PATH) -> None:
    init_db(db_path)
    with connect(db_path) as con:
        con.execute(
            'UPDATE discovery_runs SET status=?, finished_at=? WHERE task_id=?',
            (status, int(time.time()), task_id),
        )


def get_run(task_id: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    with connect(db_path) as con:
        row = con.execute('SELECT * FROM discovery_runs WHERE task_id=?', (task_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d['planned_queries'] = json.loads(d.get('planned_queries_json') or '[]')
    except Exception:
        d['planned_queries'] = []
    return d


def list_runs(
    db_path: str = DEFAULT_DB_PATH,
    persona: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    init_db(db_path)
    sql = 'SELECT * FROM discovery_runs '
    params: List[Any] = []
    if persona:
        sql += 'WHERE persona=? '
        params.append(persona)
    sql += 'ORDER BY started_at DESC LIMIT ?'
    params.append(int(limit))

    with connect(db_path) as con:
        rows = con.execute(sql, params).fetchall()

    out: List[Dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        try:
            d['planned_queries'] = json.loads(d.get('planned_queries_json') or '[]')
        except Exception:
            d['planned_queries'] = []
        out.append(d)
    return out


def latest_run(persona: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    with connect(db_path) as con:
        row = con.execute(
            'SELECT * FROM discovery_runs WHERE persona=? ORDER BY started_at DESC LIMIT 1',
            (persona,),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d['planned_queries'] = json.loads(d.get('planned_queries_json') or '[]')
    except Exception:
        d['planned_queries'] = []
    return d
