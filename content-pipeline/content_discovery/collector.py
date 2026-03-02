#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_local_tavily_key() -> str:
    """Load Tavily key from local secrets files when env is not set.

    Priority:
    - content-pipeline/config/secrets.local.json
    - content-pipeline/config/secrets.json
    """
    try:
        base_dir = Path(__file__).resolve().parents[1]
        for name in ('secrets.local.json', 'secrets.json'):
            p = base_dir / 'config' / name
            if not p.exists():
                continue
            data = json.loads(p.read_text(encoding='utf-8'))
            key = ((data.get('tavily') or {}).get('api_key') or '').strip()
            if key and not key.upper().startswith('YOUR_'):
                return key
    except Exception:
        return ''
    return ''


def tavily_search(query: str, max_results: int = 8, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Call Tavily Search API.

    Returns Tavily `results` list as-is. Each result usually contains:
    - title
    - url
    - content (snippet)
    - score (provider-specific)
    """

    key = (api_key or os.environ.get('TAVILY_API_KEY') or '').strip()
    if not key:
        key = _load_local_tavily_key()
    if not key:
        raise RuntimeError('Missing TAVILY_API_KEY')

    payload = {
        'api_key': key,
        'query': query,
        'max_results': int(max_results),
        'include_answer': False,
    }

    req = urllib.request.Request(
        'https://api.tavily.com/search',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    with urllib.request.urlopen(req, timeout=25) as r:
        data = json.loads(r.read().decode('utf-8', errors='ignore'))

    return data.get('results', []) or []


def estimate_heat(result: Dict[str, Any], rank: int) -> Dict[str, Any]:
    """Heuristic heat score in absence of platform likes/reads.

    - Use Tavily score if present.
    - Reward higher rank.
    """

    score = result.get('score')
    base = 50.0
    ev = []

    if isinstance(score, (int, float)):
        # Tavily score is not standardized; clamp into a gentle range
        base = max(0.0, min(100.0, float(score) * 100.0))
        ev.append(f"tavily_score={score}")

    # rank bonus (1 is best)
    rank_bonus = max(0.0, 14.0 - (rank - 1) * 2.0)
    ev.append(f"rank_bonus={rank_bonus}")

    heat = max(0.0, min(100.0, base * 0.7 + rank_bonus * 2.0))
    return {'heat_score': heat, 'heat_evidence': '; '.join(ev)}


def now_ts() -> int:
    return int(time.time())
