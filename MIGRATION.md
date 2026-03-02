# Migration Notes

This repo is intended to be portable across servers/accounts.

## What You Need To Change

- Copy `.env.example` to `.env` and fill in keys.
- If you use `content-pipeline/config/secrets.json` (optional), update it for the new server.

## Key Paths

- All runtime paths are now resolved relative to the `content-pipeline/` folder (no hard-coded `/root/.openclaw/workspace` paths).
- Discovery DB default: `content-pipeline/content_discovery/discovery.db` (override via `DISCOVERY_DB_PATH`).

## Quick Start

```bash
cd content-pipeline
python3 article_library/web_server.py
```

## Data Included

This repo intentionally includes local sqlite DB files and workspace skills so the system can be migrated and used immediately.

- `content-pipeline/article_library/library.db`
- `content-pipeline/database/content.db`
- `content-pipeline/content_discovery/discovery.db`
- `content-pipeline/user_preferences.db`
- `skills/`
