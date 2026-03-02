#!/usr/bin/env python3
"""
内容自动化Pipeline - 完整版
支持：RSS采集 → AI选题 → AI撰写 → 审核通知 → 自动/手动发布 → 定时任务
"""

import os
import sys
import json
import logging
import requests
import subprocess
from datetime import datetime
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from fetcher.rss_collector import RSSCollector
from generator.content_generator import ContentGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(Path(__file__).resolve().parent / 'logs' / 'pipeline.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContentPipeline:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent
        self.config = self._load_config()
        self.memory = self._load_memory()
        self.collector = RSSCollector()
        self.generator = ContentGenerator()
        
        # 飞书/企微通知配置
        self.notify_channel = 'feishu'  # 或 'wecom-app'
        
    def _load_config(self):
        config_path = self.base_dir / 'config' / 'pipeline.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_memory(self):
        memory_path = self.base_dir / 'memory' / 'published.json'
        if memory_path.exists():
            with open(memory_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'articles': [], 'topics': [], 'pending_review': []}
    
    def _save_memory(self):
        memory_path = self.base_dir / 'memory' / 'published.json'
        with open(memory_path, 'w', encoding='utf-8') as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)
    
    def notify_user(self, title, content, actions=None):
        """通知用户审核"""
        logger.info(f"📢 发送通知: {title}")
        
        # 构建通知消息
        message = f"""📝 **文章待审核**

**标题**: {title}

**摘要**:
{content[:500]}...

**操作**:
1. 查看完整文章: `/content-pipeline/output/article_*.md`
2. 确认发布: 回复 "发布"
3. 重新生成: 回复 "重新生成 [新的选题方向]"
4. 跳过今日: 回复 "跳过"

**截止时间**: 30分钟内未回复将自动发布到草稿箱
"""
        
        # 这里可以通过飞书/企微API发送
        # 目前先输出到日志
        logger.info(f"\n{'='*60}")
        logger.info(message)
        logger.info(f"{'='*60}\n")
        
        return True
    
    def step1_collect(self):
        """步骤1: 采集热点资讯"""
        logger.info("=== 步骤1: 采集热点资讯 ===")
        
        items = self.collector.collect_all()
        if not items:
            logger.warning("未采集到有效资讯")
            return []
        
        scored_items = self.collector.score_items(items)
        top_items = scored_items[:10]
        logger.info(f"✅ 采集完成，精选 {len(top_items)} 条")
        
        return top_items
    
    def step2_analyze(self, collected_items):
        """步骤2: AI分析选题角度"""
        logger.info("=== 步骤2: AI分析选题角度 ===")
        
        recent_topics = [a.get('topic', '') for a in self.memory.get('articles', [])[-20:]]
        analysis = self.generator.analyze_topic(collected_items, recent_topics)
        
        logger.info(f"✅ 选定选题: {analysis.get('title', 'AI时代的学习与成长')}")
        return analysis
    
    def step3_write(self, angle_info):
        """步骤3: 撰写文章"""
        logger.info("=== 步骤3: AI撰写文章 ===")
        
        article = self.generator.write_article(angle_info)
        
        # 清理markdown代码块标记
        article = article.replace('```markdown\n', '').replace('\n```', '')
        
        return article
    
    def step4_save(self, article, topic):
        """步骤4: 保存文章并等待审核"""
        logger.info("=== 步骤4: 保存并通知审核 ===")
        
        today = datetime.now().strftime('%Y%m%d')
        output_path = self.base_dir / 'output' / f'article_{today}.md'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(article)
        
        logger.info(f"✅ 文章已保存: {output_path}")
        
        # 添加到待审核列表
        review_item = {
            'date': datetime.now().isoformat(),
            'topic': topic,
            'path': str(output_path),
            'status': 'pending_review'
        }
        self.memory['pending_review'].append(review_item)
        self._save_memory()
        
        # 发送通知
        self.notify_user(topic, article)
        
        return output_path
    
    def step5_publish(self, article_path, auto_publish=False):
        """步骤5: 发布到微信公众号草稿箱"""
        logger.info("=== 步骤5: 发布到草稿箱 ===")
        
        if not auto_publish:
            logger.info("⏳ 等待审核中... (设置 auto_publish=True 可自动发布)")
            return None
        
        try:
            # 使用wenyan-cli发布
            result = subprocess.run(
                ['wenyan', 'publish', '-f', str(article_path), '-t', 'lapis', '-h', 'solarized-light'],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, 'WECHAT_APP_ID': 'wx5c6f2e9b5734ddd5', 'WECHAT_APP_SECRET': 'baf071b9ca8e805992a26111c552b9f9'}
            )
            
            if '上传成功' in result.stdout or 'media_id' in result.stdout:
                logger.info("✅ 发布成功")
                return result.stdout
            else:
                logger.warning(f"⚠️ 发布返回: {result.stdout} {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 发布失败: {e}")
            return None
    
    def run(self, auto_publish=False, skip_review=False):
        """执行完整Pipeline"""
        logger.info("🚀 启动内容自动化Pipeline")
        
        try:
            # 步骤1: 采集
            collected = self.step1_collect()
            if not collected:
                logger.warning("未采集到有效资讯，Pipeline终止")
                return False
            
            # 步骤2: 分析
            angle = self.step2_analyze(collected)
            topic = angle.get('title', 'AI时代的学习与成长')
            
            # 步骤3: 撰写
            article = self.step3_write(angle)
            
            # 步骤4: 保存并通知审核
            article_path = self.step4_save(article, topic)
            
            # 步骤5: 发布（如果设置自动发布或跳过审核）
            if auto_publish or skip_review:
                self.step5_publish(article_path, auto_publish=True)
                status = 'published'
            else:
                logger.info("⏳ 文章已保存，等待人工审核后发布")
                logger.info(f"   文件: {article_path}")
                status = 'pending_review'
            
            # 更新记忆
            self.memory['articles'].append({
                'date': datetime.now().isoformat(),
                'topic': topic,
                'path': str(article_path),
                'status': status
            })
            self._save_memory()
            
            logger.info("✅ Pipeline执行完成！")
            return True
            
        except Exception as e:
            logger.error(f"❌ Pipeline执行失败: {e}", exc_info=True)
            return False
    
    def review_and_publish(self, article_date=None, action='publish'):
        """审核并发布指定文章"""
        if article_date is None:
            article_date = datetime.now().strftime('%Y%m%d')
        
        article_path = self.base_dir / 'output' / f'article_{article_date}.md'
        
        if not article_path.exists():
            logger.error(f"❌ 文章不存在: {article_path}")
            return False
        
        if action == 'publish':
            result = self.step5_publish(article_path, auto_publish=True)
            if result:
                logger.info("✅ 文章已发布到微信公众号草稿箱")
                return True
        elif action == 'skip':
            logger.info("⏭️ 跳过发布")
            return True
        
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Content Pipeline')
    parser.add_argument('--auto-publish', action='store_true', help='自动发布（跳过审核）')
    parser.add_argument('--review', type=str, help='审核并发布指定日期文章 (YYYYMMDD)')
    parser.add_argument('--action', type=str, default='publish', choices=['publish', 'skip'], help='审核动作')
    
    args = parser.parse_args()
    
    pipeline = ContentPipeline()
    
    if args.review:
        # 审核模式
        success = pipeline.review_and_publish(args.review, args.action)
        sys.exit(0 if success else 1)
    else:
        # 正常运行
        success = pipeline.run(auto_publish=args.auto_publish)
        sys.exit(0 if success else 1)
