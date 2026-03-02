#!/usr/bin/env python3
"""
通过 SendClaw API 检查审核回复邮件
替代原来的 Zapier + IMAP 方案
"""
import json
import os
import urllib.request
import urllib.error
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
SECRETS_PATH = BASE_DIR / 'config/secrets.json'
SECRETS_LOCAL_PATH = BASE_DIR / 'config/secrets.local.json'
DB_PATH = BASE_DIR / 'database/pipeline.db'


def load_secrets() -> dict:
    if SECRETS_LOCAL_PATH.exists():
        return json.loads(SECRETS_LOCAL_PATH.read_text(encoding='utf-8'))
    return json.loads(SECRETS_PATH.read_text(encoding='utf-8'))


def sendclaw_request(path: str, api_key: str) -> dict:
    """调用 SendClaw API"""
    req = urllib.request.Request(
        f'https://sendclaw.com/api{path}',
        headers={'X-Api-Key': api_key}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def parse_reply(body: str) -> dict:
    """解析审核回复内容"""
    result = {'action': None, 'candidate': None, 'feedback': ''}

    # 识别选择指令：选A / 选B / 选C / A / B / C
    match = re.search(r'[选择]?\s*([ABC])\b', body.upper())
    if match:
        result['action'] = 'select'
        result['candidate'] = match.group(1)

    # 识别修改指令
    if '修改' in body or '改' in body:
        result['action'] = 'revise'

    # 识别拒绝指令
    if '拒绝' in body or '不要' in body or '重新' in body:
        result['action'] = 'reject'

    result['feedback'] = body.strip()
    return result


def process_replies():
    secrets = load_secrets()
    api_key = (secrets.get('sendclaw') or {}).get('api_key')
    if not api_key:
        api_key = (os.environ.get('SENDCLAW_API_KEY') or '').strip()

    if not api_key:
        raise SystemExit('Missing SendClaw API key: set SENDCLAW_API_KEY or fill config/secrets.local.json')

    # 检查未读数
    check = sendclaw_request('/mail/check', api_key)
    unread = check.get('unreadCount', 0)
    print(f'未读邮件: {unread}')

    if unread == 0:
        print('没有新回复')
        return

    # 获取未读邮件
    messages = sendclaw_request('/mail/messages?unread=true&limit=10', api_key)
    for msg in messages.get('messages', []):
        subject = msg.get('subject', '')
        body = msg.get('bodyText', '')
        from_addr = msg.get('fromAddress', '')
        print(f'\n📧 来自: {from_addr}')
        print(f'   主题: {subject}')
        print(f'   内容: {body[:200]}')

        parsed = parse_reply(body)
        print(f'   解析: {parsed}')

        if parsed['action'] == 'select' and parsed['candidate']:
            print(f'   ✅ 用户选择了候选 {parsed["candidate"]}')
            # TODO: 触发对应候选的发布流程
        elif parsed['action'] == 'revise':
            print(f'   ✏️ 用户要求修改')
        elif parsed['action'] == 'reject':
            print(f'   ❌ 用户拒绝，需要重新生成')


if __name__ == '__main__':
    process_replies()
