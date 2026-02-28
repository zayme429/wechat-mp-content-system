# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## 🔐 WeChat Official Account (微信公众号)

**API Credentials:**
```bash
export WECHAT_APP_ID=wx5c6f2e9b5734ddd5
export WECHAT_APP_SECRET=baf071b9ca8e805992a26111c552b9f9
```

**配置说明:**
- AppID 和 AppSecret 来自微信公众号后台
- IP 白名单已添加当前服务器
- 发布工具: wenyan-cli

---

Add whatever helps you do your job. This is your cheat sheet.
