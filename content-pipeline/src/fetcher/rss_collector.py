#!/usr/bin/env python3
"""
RSS采集器 - 获取科技/AI资讯
"""

import feedparser
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class RSSCollector:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = Path('/root/.openclaw/workspace/content-pipeline/config/pipeline.json')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.rss_sources = config.get('rss_sources', {})
        self.keywords = config.get('keywords', {}).get('high_priority', [])
        
    def fetch_feed(self, url, name):
        """抓取单个RSS源"""
        try:
            logger.info(f"Fetching: {name} ({url})")
            
            # 添加请求头避免被拦截
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # 使用requests获取原始内容
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            
            # 解析RSS
            feed = feedparser.parse(response.text)
            
            items = []
            for entry in feed.entries[:10]:  # 只取最近10条
                item = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', entry.get('description', ''))[:300],
                    'published': entry.get('published', ''),
                    'source': name
                }
                items.append(item)
            
            logger.info(f"  ✓ Got {len(items)} items from {name}")
            return items
            
        except Exception as e:
            logger.error(f"  ✗ Failed to fetch {name}: {e}")
            return []
    
    def collect_all(self):
        """采集所有RSS源"""
        logger.info("=== RSS采集开始 ===")
        
        all_items = []
        
        # 遍历所有分类的RSS源
        for category, sources in self.rss_sources.items():
            logger.info(f"\n[{category}] 类别:")
            for source in sources:
                items = self.fetch_feed(source['url'], source['name'])
                
                # 添加分类标签
                for item in items:
                    item['category'] = category
                    item['tags'] = source.get('tags', [])
                
                all_items.extend(items)
        
        logger.info(f"\n✅ RSS采集完成，共 {len(all_items)} 条")
        return all_items
    
    def score_items(self, items):
        """根据关键词给文章打分"""
        logger.info("=== 热点评分 ===")
        
        scored_items = []
        
        for item in items:
            score = 0
            title_summary = f"{item['title']} {item['summary']}".lower()
            
            # 高优先级关键词匹配
            for keyword in self.keywords:
                if keyword.lower() in title_summary:
                    score += 10
            
            # 根据来源权重加分
            for category, sources in self.rss_sources.items():
                for source in sources:
                    if source['name'] == item['source']:
                        score += source.get('weight', 3)
            
            item['hot_score'] = score
            scored_items.append(item)
        
        # 按分数排序
        scored_items.sort(key=lambda x: x['hot_score'], reverse=True)
        
        logger.info(f"✅ 评分完成，最高分: {scored_items[0]['hot_score'] if scored_items else 0}")
        return scored_items

if __name__ == '__main__':
    # 测试
    collector = RSSCollector()
    items = collector.collect_all()
    scored = collector.score_items(items)
    
    # 输出前5条
    print("\n=== 热点TOP5 ===")
    for i, item in enumerate(scored[:5], 1):
        print(f"{i}. [{item['hot_score']}] {item['title'][:50]}... ({item['source']})")
