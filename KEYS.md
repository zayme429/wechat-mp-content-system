# Keys / Secrets Configuration

This repo is designed to be migrated to a new server/account easily.

Principles:
- No real keys should be committed.
- Use `.env` (recommended) or `content-pipeline/config/secrets.json` (optional local convenience).

## Option A: `.env` (Recommended)

```bash
cp .env.example .env
# edit .env
```

Minimum required (push to WeChat draft box):
- `WECHAT_APP_ID`
- `WECHAT_APP_SECRET`

Common optional keys:
- `KIMI_API_KEY` (LLM generation via OpenAI-compatible `/chat/completions`)
- `KIMI_BASE_URL` (your GPT gateway base URL, or Moonshot default)
- `KIMI_MODEL` (default: `kimi-k2.5`)
- `OPENAI_API_KEY` (embeddings / vector recall; OpenAI-compatible)
- `OPENAI_BASE_URL` (embeddings base_url; e.g. `https://api.siliconflow.cn/v1`)
- `EMBEDDING_MODEL` (e.g. `Qwen/Qwen3-Embedding-8B`)
- `EMBEDDING_DIM` (only for `text-embedding-3-*`)
- `TAVILY_API_KEY` (content discovery/search)
- `SENDCLAW_API_KEY` (review inbox polling)

## Option B: `content-pipeline/config/secrets.json` (Optional)

```bash
cp content-pipeline/config/secrets.example.json content-pipeline/config/secrets.json
# edit content-pipeline/config/secrets.json
```

Supported fields (placeholders in repo):
- `wechat.app_id`, `wechat.app_secret`
- `smtp.host`, `smtp.port`, `smtp.secure`, `smtp.user`, `smtp.pass`, `smtp.from`
- `tavily.api_key`
- `sendclaw.api_key`, `sendclaw.email`, `sendclaw.bot_id`

## Notes

- If both are set, env vars should be preferred.
- Do NOT put real keys into `TOOLS.md`.
