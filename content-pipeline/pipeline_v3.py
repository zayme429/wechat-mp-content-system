#!/usr/bin/env python3
"""
内容生产管线 v3.0
流程：主题确定 → 文献采集 → 选题设计 × 3 → 文章生成 × 3 → 审核邮件
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from fetcher.rss_collector import RSSCollector
from generator.content_generator import ContentGenerator
from database.content_db import ContentDatabase
from notification.review_mail_sender import ReviewMailSender

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(Path(__file__).resolve().parent / 'logs' / 'pipeline.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
WECHAT_SEARCH = Path.home() / '.openclaw' / 'workspace' / 'skills' / 'wechat-search' / 'wechat_search.py'



def _load_secrets():
    """加载敏感配置"""
    secrets_path = BASE_DIR / 'config' / 'secrets.local.json'
    if not secrets_path.exists():
        secrets_path = BASE_DIR / 'config' / 'secrets.json'
    if secrets_path.exists():
        with open(secrets_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    raise FileNotFoundError(
        f"secrets file not found. Expected one of:\n"
        f"- {BASE_DIR / 'config' / 'secrets.local.json'}\n"
        f"- {BASE_DIR / 'config' / 'secrets.json'}\n"
        f"Copy config/secrets.example.json to config/secrets.local.json (recommended) and fill in your values."
    )

class ContentPipelineV3:

    def __init__(self):
        self.config = self._load_json('config/pipeline.json')
        self.secrets = _load_secrets()
        self.generator = ContentGenerator()
        self.collector = RSSCollector()
        self.db = ContentDatabase()

    def _load_json(self, path):
        full = BASE_DIR / path
        return json.load(open(full)) if full.exists() else {}

    # ─────────────────────────────────────────
    # Step 1: 主题确定
    # ─────────────────────────────────────────
    def determine_topic(self, manual_topic: str = None) -> dict:
        """三种模式：手动指定 / 配置文件 / 自动热点"""
        logger.info("=== Step 1: 确定主题 ===")

        if manual_topic:
            logger.info(f"模式A: 手动指定主题 → {manual_topic}")
            return {'topic': manual_topic, 'mode': 'manual', 'keywords': [manual_topic]}

        weekly_focus = self.config.get('weekly_focus')
        if weekly_focus:
            keywords = self.config.get('search_keywords', [weekly_focus])
            logger.info(f"模式B: 配置文件主题 → {weekly_focus}")
            return {'topic': weekly_focus, 'mode': 'config', 'keywords': keywords}

        # 模式C: 自动从 RSS 热点提炼主题
        logger.info("模式C: 自动热点提炼主题")
        news = self.collector.collect_all()
        scored = self.collector.score_items(news)[:5]
        news_text = '\n'.join([f"- {n['title']} ({n['source']})" for n in scored])
        prompt = f"""根据以下热点新闻，提炼一个适合写深度文章的主题：

{news_text}

输出格式：
主题：[主题名称，10字以内]
关键词：[3-5个搜索关键词，逗号分隔]
方向：[一句话说明写作方向]"""

        result = self.generator._call_llm(prompt)
        topic = keywords = direction = ''
        for line in result.strip().split('\n'):
            if '主题：' in line or '主题:' in line:
                topic = line.split('：', 1)[-1].split(':', 1)[-1].strip()
            elif '关键词：' in line or '关键词:' in line:
                keywords = [k.strip() for k in line.split('：', 1)[-1].split(':', 1)[-1].split(',')]
            elif '方向：' in line or '方向:' in line:
                direction = line.split('：', 1)[-1].split(':', 1)[-1].strip()

        logger.info(f"自动提炼主题: {topic}")
        return {'topic': topic or '人工智能应用', 'mode': 'auto', 'keywords': keywords or [topic], 'direction': direction}

    # ─────────────────────────────────────────
    # Step 2: 文献采集
    # ─────────────────────────────────────────
    def collect_literature(self, topic_info: dict) -> list:
        """搜索并抓取文献全文 - 使用 Tavily Search API"""
        logger.info("=== Step 2: 文献采集 ===")
        keywords = topic_info.get('keywords', [topic_info['topic']])
        literature = []

        for kw in keywords[:3]:
            logger.info(f"搜索关键词: {kw}")

            # 微信公众号搜索
            try:
                results = self._tavily_search(f"{kw} site:mp.weixin.qq.com", max_results=5)
                for r in results:
                    literature.append({
                        'title': r.get('title', ''),
                        'url': r.get('url', ''),
                        'source': '微信公众号',
                        'summary': r.get('content', '')[:300],
                        'full_text': r.get('content', ''),
                        'search_keyword': kw
                    })
                logger.info(f"  微信搜索: {len(results)} 篇")
            except Exception as e:
                logger.warning(f"  微信搜索失败: {e}")

            # 通用搜索
            try:
                results = self._tavily_search(f"{kw} 深度分析", max_results=5)
                for r in results:
                    if 'mp.weixin.qq.com' not in r.get('url', ''):
                        literature.append({
                            'title': r.get('title', ''),
                            'url': r.get('url', ''),
                            'source': r.get('url', '').split('/')[2] if r.get('url') else '网络',
                            'summary': r.get('content', '')[:300],
                            'full_text': r.get('content', ''),
                            'search_keyword': kw
                        })
                logger.info(f"  通用搜索: {len(results)} 篇")
            except Exception as e:
                logger.warning(f"  通用搜索失败: {e}")

        # 去重
        seen = set()
        unique = []
        for item in literature:
            if item['title'] and item['title'] not in seen:
                seen.add(item['title'])
                unique.append(item)

        # 对没有全文的条目尝试抓取
        for item in unique[:15]:
            if not item['full_text'] and item['url']:
                try:
                    item['full_text'] = self._fetch_full_text(item['url'])[:3000]
                    logger.info(f"  ✓ 抓取全文: {item['title'][:40]}...")
                except Exception:
                    pass

        result = unique[:15]
        logger.info(f"✅ 文献采集完成，共 {len(result)} 篇")
        return result

    def _tavily_search(self, query: str, max_results: int = 5) -> list:
        """调用 Tavily Search API"""
        import urllib.request
        api_key = os.environ.get('TAVILY_API_KEY') or self.secrets.get('tavily', {}).get('api_key', '')
        data = json.dumps({
            'api_key': api_key,
            'query': query,
            'max_results': max_results,
            'include_answer': False
        }).encode()
        req = urllib.request.Request(
            'https://api.tavily.com/search',
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read())
        return result.get('results', [])

    def _fetch_full_text(self, url: str) -> str:
        """抓取文章全文"""
        import urllib.request
        import html
        import re
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8', errors='ignore')
        # 简单提取正文
        raw = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL)
        raw = re.sub(r'<style[^>]*>.*?</style>', '', raw, flags=re.DOTALL)
        raw = re.sub(r'<[^>]+>', ' ', raw)
        raw = html.unescape(raw)
        raw = re.sub(r'\s+', ' ', raw).strip()
        return raw

    # ─────────────────────────────────────────
    # Step 3: 选题设计 × 3
    # ─────────────────────────────────────────
    def design_topics(self, topic_info: dict, literature: list) -> list:
        """为每个候选独立设计选题"""
        logger.info("=== Step 3: 选题设计 ===")

        # 构建文献摘要供 LLM 参考
        lit_summary = ""
        for i, item in enumerate(literature, 1):
            lit_summary += f"\n[{i}] {item['title']}\n来源: {item['source']} | URL: {item['url']}\n摘要: {item['summary'][:200]}\n"

        prompt = f"""你是一位资深科技专栏编辑。

主题：{topic_info['topic']}
写作方向：{topic_info.get('direction', '深度分析+实用建议')}

以下是收集到的文献资料：
{lit_summary}

请为3篇候选文章分别设计选题方案，每篇选题必须：
1. 角度不同（实战/深度/故事 三种之一）
2. 从上述文献中选3篇最相关的作为参考（用编号[1][2][3]等标注）
3. 选题之间不重复

输出格式（严格按此格式）：

===候选1===
题目：[文章标题]
角度：实战派
摘要：[200字写作方向说明]
参考文献：[1][3][5]
选题理由：[为什么选这个角度和这些文献]

===候选2===
题目：[文章标题]
角度：深度派
摘要：[200字写作方向说明]
参考文献：[2][4][6]
选题理由：[为什么选这个角度和这些文献]

===候选3===
题目：[文章标题]
角度：故事派
摘要：[200字写作方向说明]
参考文献：[1][7][9]
选题理由：[为什么选这个角度和这些文献]"""

        result = self.generator._call_llm(prompt)
        topics = self._parse_topic_designs(result, literature)
        logger.info(f"✅ 选题设计完成，共 {len(topics)} 个候选")
        return topics

    def _parse_topic_designs(self, result: str, literature: list) -> list:
        """解析选题设计结果"""
        topics = []
        blocks = result.split('===候选')
        for block in blocks[1:]:
            lines = block.strip().split('\n')
            topic = {'title': '', 'angle': '', 'summary': '', 'refs': [], 'reason': ''}
            for line in lines:
                if '题目：' in line or '题目:' in line:
                    topic['title'] = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                elif '角度：' in line or '角度:' in line:
                    topic['angle'] = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                elif '摘要：' in line or '摘要:' in line:
                    topic['summary'] = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                elif '参考文献：' in line or '参考文献:' in line:
                    import re
                    indices = [int(x)-1 for x in re.findall(r'\[(\d+)\]', line)]
                    topic['refs'] = [literature[i] for i in indices if i < len(literature)]
                elif '选题理由：' in line or '选题理由:' in line:
                    topic['reason'] = line.split('：', 1)[-1].split(':', 1)[-1].strip()
            if topic['title']:
                topics.append(topic)
        return topics

    # ─────────────────────────────────────────
    # Step 4: 文章生成 × 3
    # ─────────────────────────────────────────
    def generate_articles(self, topic_designs: list) -> list:
        """根据选题设计生成文章"""
        logger.info("=== Step 4: 文章生成 ===")
        candidates = []

        for i, design in enumerate(topic_designs, 1):
            logger.info(f"生成候选 {i}: {design['title']}")

            # 构建参考文献内容
            refs_text = ""
            for j, ref in enumerate(design['refs'], 1):
                refs_text += f"\n参考{j}：{ref['title']}\n来源：{ref['source']}\n内容：{ref.get('full_text', ref.get('summary', ''))[:1000]}\n"

            writing_rules = self.config.get('content_strategy', {}).get('writing_rules', [])
            rules_text = '\n'.join([f'{i+6}. {r}' for i, r in enumerate(writing_rules)])

            prompt = f"""你是一位资深科技专栏作家。

文章题目：{design['title']}
写作角度：{design['angle']}
写作方向：{design['summary']}

参考文献（请在文章中引用，格式：[来源名称]）：
{refs_text}

写作要求：
1. 1500-2000字
2. 结构：引言→现象分析→深度洞察→行动建议→结语
3. 必须引用参考文献中的具体数据或观点，并标注来源
4. 风格：{design['angle']}，有温度，有洞见
5. 拒绝陈词滥调和贩卖焦虑
{rules_text}

直接输出文章正文，不要输出其他内容。"""

            article = self.generator._call_llm(prompt)
            quality_score = self._score_quality(article)

            candidates.append({
                'topic': design['title'],
                'angle': design['summary'],
                'angle_type': design['angle'],
                'content': article,
                'quality_score': quality_score,
                'uniqueness_score': 7.5,
                'word_count': len(article),
                # 溯源信息
                'source_news': [{'title': r['title'], 'source': r['source'], 'url': r['url']} for r in design['refs']],
                'angle_reason': design['reason'],
                'topic_summary': design['summary'],
            })
            logger.info(f"  ✅ 候选 {i} 生成完成，质量分: {quality_score}")

        return candidates

    def _score_quality(self, content: str) -> float:
        score = 5.0
        if '案例' in content or '例如' in content: score += 1
        if '%' in content or '数据' in content: score += 1
        if '建议' in content or '方法' in content: score += 1
        if len(content) >= 1200: score += 1
        if '【' in content or '[' in content: score += 0.5  # 有引用标注
        return min(score, 10)

    # ─────────────────────────────────────────
    # Step 5: 保存 + 发送审核邮件 + 推草稿
    # ─────────────────────────────────────────
    def send_review_and_push(self, candidates: list, topic_info: dict):
        logger.info("=== Step 5: 审核邮件 + 草稿箱 ===")
        today = datetime.now().strftime('%Y%m%d')

        # 保存候选文件
        output_dir = BASE_DIR / 'output' / today
        output_dir.mkdir(parents=True, exist_ok=True)
        for i, c in enumerate(candidates, 1):
            file_path = output_dir / f'candidate_{i}.md'
            title = c['topic'].replace('"', '').replace("'", '')
            cover = 'https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=900'
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"---\ntitle: {title}\ntype: {c['angle_type']}\nquality_score: {c['quality_score']}\ncover: {cover}\n---\n\n")
                f.write(c['content'])

        # 保存到数据库
        best = max(candidates, key=lambda x: x['quality_score'])
        article_id = self.db.save_article(
            date=today, topic=best['topic'],
            content=best['content'], candidates=candidates, status='pending_review'
        )
        logger.info(f"✅ 保存数据库 ID: {article_id}")

        # 发送审核邮件
        smtp = self.secrets['smtp']
        smtp['zapier_email'] = self.secrets['review']['zapier_email']
        mail_sender = ReviewMailSender(smtp)
        mail_sender.send_html_review_email(
            to=self.secrets['review']['recipient'],
            candidates=candidates,
            article_date=today,
            topic_info=topic_info,
            literature=self._current_literature
        )

        # 推最高分候选到草稿箱
        best_idx = candidates.index(best) + 1
        best_file = output_dir / f'candidate_{best_idx}.md'
        try:
            result = subprocess.run(
                ['wenyan', 'publish', '-f', str(best_file), '-t', 'lapis', '-h', 'solarized-light'],
                capture_output=True, text=True, timeout=120,
                env={**os.environ, 'WECHAT_APP_ID': self.secrets['wechat']['app_id'], 'WECHAT_APP_SECRET': self.secrets['wechat']['app_secret']}
            )
            if '上传成功' in result.stdout or 'media_id' in result.stdout:
                logger.info(f"✅ 候选 {best_idx}「{best['topic']}」已推送到草稿箱")
            else:
                logger.warning(f"⚠️ 草稿箱推送失败: {result.stderr[:200]}")
        except Exception as e:
            logger.warning(f"⚠️ 草稿箱推送异常: {e}")

    # ─────────────────────────────────────────
    # 主入口
    # ─────────────────────────────────────────
    def run(self, manual_topic: str = None):
        logger.info("🚀 启动内容生产管线 v3.0")
        try:
            topic_info = self.determine_topic(manual_topic)
            literature = self.collect_literature(topic_info)
            if not literature:
                logger.error("文献采集失败，终止")
                return False
            self._current_literature = literature
            topic_designs = self.design_topics(topic_info, literature)
            if not topic_designs:
                logger.error("选题设计失败，终止")
                return False
            candidates = self.generate_articles(topic_designs)
            self.send_review_and_push(candidates, topic_info)
            logger.info("✅ 管线完成")
            return True
        except Exception as e:
            logger.error(f"❌ 管线失败: {e}", exc_info=True)
            return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', type=str, help='手动指定主题')
    args = parser.parse_args()
    pipeline = ContentPipelineV3()
    success = pipeline.run(manual_topic=args.topic)
    sys.exit(0 if success else 1)
