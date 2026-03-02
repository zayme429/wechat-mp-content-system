#!/usr/bin/env python3
"""
高级内容管理Pipeline v2.0
支持：多候选生成、系统化审核、反馈固化、偏好学习
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
from generator.multi_candidate import MultiCandidateGenerator
from database.content_db import ContentDatabase
from feedback.solidifier import FeedbackSolidifier
from notification.email_notifier import EmailNotifier
from notification.review_mail_sender import ReviewMailSender

# 导入邮件审核 skill
sys.path.insert(0, str(Path.home() / '.openclaw' / 'workspace' / 'skills' / 'content-review-mail' / 'scripts'))
from content_review_mail import ContentReviewMail

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(Path(__file__).resolve().parent / 'logs' / 'pipeline.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def _load_secrets():
    """加载敏感配置"""
    secrets_path = Path(__file__).resolve().parent / 'config' / 'secrets.local.json'
    if not secrets_path.exists():
        secrets_path = Path(__file__).resolve().parent / 'config' / 'secrets.json'
    if secrets_path.exists():
        with open(secrets_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    raise FileNotFoundError(
        f"secrets file not found. Expected one of:\n"
        f"- {Path(__file__).resolve().parent / 'config' / 'secrets.local.json'}\n"
        f"- {Path(__file__).resolve().parent / 'config' / 'secrets.json'}\n"
        f"Copy config/secrets.example.json to config/secrets.local.json (recommended) and fill in your values."
    )

class AdvancedContentPipeline:
    """高级内容管理Pipeline"""
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent
        
        # 加载配置
        self.config = self._load_json('config/pipeline.json')
        self.secrets = _load_secrets()
        self.system_config = self._load_json('config/content_system.json')
        
        # 初始化组件
        self.collector = RSSCollector()
        self.multi_generator = MultiCandidateGenerator()
        self.db = ContentDatabase()
        self.solidifier = FeedbackSolidifier()
        self.email = EmailNotifier()
        self.review_mail = ContentReviewMail()
        
    def _load_json(self, path):
        """加载JSON配置"""
        full_path = self.base_dir / path
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def run_multi_candidate_workflow(self, count=3):
        """运行多候选工作流"""
        logger.info("🚀 启动多候选内容生成工作流")
        
        today = datetime.now().strftime('%Y%m%d')
        
        try:
            # 步骤1: 采集热点
            logger.info("=== 步骤1: 采集热点资讯 ===")
            news_items = self.collector.collect_all()
            if not news_items:
                logger.error("未采集到资讯，终止")
                return False
            
            scored_items = self.collector.score_items(news_items)
            top_items = scored_items[:10]
            
            # 步骤2: 获取历史主题（用于去重）
            recent_topics = [a['topic'] for a in self.db.get_article_history(limit=20)]
            
            # 步骤3: 生成多候选
            logger.info(f"=== 步骤2: 生成 {count} 个候选 ===")
            candidates = self.multi_generator.generate_candidates(
                top_items, recent_topics, count=count
            )
            
            if not candidates:
                logger.error("候选生成失败")
                return False
            
            # 步骤4: 保存到数据库
            logger.info("=== 步骤3: 保存候选到数据库 ===")
            
            # 选择最高分候选作为主文章
            best_candidate = max(candidates, key=lambda x: x['quality_score'] + x['uniqueness_score'])
            
            article_id = self.db.save_article(
                date=today,
                topic=best_candidate['topic'],
                content=best_candidate['content'],
                candidates=candidates,
                status='pending_review'
            )
            
            logger.info(f"✅ 文章已保存，ID: {article_id}")
            
            # 步骤5: 发送审核邮件
            logger.info("=== 步骤4: 发送审核邮件 ===")
            
            # 保存候选文件供查看
            self._save_candidates_for_review(today, candidates)
            
            # 步骤5: 发送审核邮件（使用优化版HTML邮件发送器）
            logger.info("=== 步骤4: 发送审核邮件（HTML完整版） ===")
            
            # 读取完整文章内容
            candidates_with_content = []
            for i, c in enumerate(candidates, 1):
                candidate_file = self.base_dir / 'output' / today / f'candidate_{i}.md'
                if candidate_file.exists():
                    with open(candidate_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 提取正文（去掉frontmatter）
                        body_start = content.find('---', content.find('---') + 3) + 3
                        full_content = content[body_start:].strip()
                        c['content'] = full_content
                candidates_with_content.append(c)
            
            # 使用新的HTML邮件发送器
            smtp_config = {
                'host': 'smtp.163.com',
                'port': 465,
                **self.secrets['smtp']
            }
            mail_sender = ReviewMailSender(smtp_config)
            email_sent = mail_sender.send_html_review_email(
                to=self.secrets['review']['recipient'],
                candidates=candidates_with_content,
                article_date=today
            )
            
            if email_sent:
                logger.info("✅ HTML审核邮件已发送（完整文章+优化排版）")
            else:
                logger.warning("⚠️ 邮件发送失败，输出到控制台")
                self._output_console_notification(candidates, today)

            # 步骤5: 推送评分最高的候选到微信草稿箱
            logger.info("=== 步骤5: 推送主推候选到草稿箱 ===")
            best_idx = candidates.index(best_candidate) + 1
            pushed = self._publish_candidate(today, best_idx)
            if pushed:
                logger.info(f"✅ 候选 {best_idx}「{best_candidate['topic']}」已推送到草稿箱")
            else:
                logger.warning("⚠️ 草稿箱推送失败，可手动执行：python3 pipeline_v2.py --select {today} --candidate {best_idx}")
            
            logger.info("✅ 多候选工作流完成，等待审核")
            return True
            
        except Exception as e:
            logger.error(f"❌ 工作流失败: {e}", exc_info=True)
            return False
    
    def _save_candidates_for_review(self, date: str, candidates: list):
        """保存候选供审核"""
        output_dir = self.base_dir / 'output' / date
        output_dir.mkdir(exist_ok=True)
        
        for i, c in enumerate(candidates, 1):
            file_path = output_dir / f'candidate_{i}.md'
            with open(file_path, 'w', encoding='utf-8') as f:
                # YAML frontmatter - 避免特殊字符导致解析错误
                title = c['topic'].replace('"', '').replace("'", '')
                angle = c.get('angle', '').replace('"', '').replace("'", '')
                angle_type = c.get('angle_type', '').replace('"', '').replace("'", '')
                # 默认封面（微信公众号要求必须有封面）
                cover = c.get('cover', 'https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=900')
                f.write(f"---\n")
                f.write(f"title: {title}\n")
                f.write(f"angle: {angle}\n")
                f.write(f"type: {angle_type}\n")
                f.write(f"quality_score: {c['quality_score']}\n")
                f.write(f"uniqueness_score: {c['uniqueness_score']}\n")
                f.write(f"cover: {cover}\n")
                f.write(f"---\n\n")
                f.write(c['content'])
        
        logger.info(f"✅ 候选已保存到: {output_dir}")
    
    def _output_console_notification(self, candidates: list, date: str):
        """输出到控制台（邮件备选）"""
        print("\n" + "="*70)
        print("📄 内容审核通知")
        print("="*70)
        print(f"日期: {date}")
        print(f"候选数量: {len(candidates)}")
        print("\n候选列表:")
        
        for i, c in enumerate(candidates, 1):
            print(f"\n候选 {i}: {c['topic']}")
            print(f"  角度: {c['angle_type']}")
            print(f"  质量分: {c['quality_score']:.1f} | 独特分: {c['uniqueness_score']:.1f}")
            print(f"  字数: {c['word_count']}")
        
        print("\n审核操作:")
        print(f"  1. 查看候选: /output/{date}/candidate_[1-3].md")
        print(f"  2. 选择发布: python pipeline.py --select {date} --candidate [1-3]")
        print(f"  3. 重新生成: python pipeline.py --regenerate {date} --direction '[方向]'")
        print(f"  4. 查看反馈指南: cat REVIEW_GUIDE.md")
        print("="*70 + "\n")
    
    def process_review(self, date: str, action: str, **kwargs):
        """处理审核"""
        logger.info(f"处理审核: {date}, 动作: {action}")
        
        if action == 'select':
            # 选择候选发布
            candidate_num = kwargs.get('candidate_num', 1)
            return self._publish_candidate(date, candidate_num)
            
        elif action == 'regenerate':
            # 重新生成
            direction = kwargs.get('direction', '')
            return self._regenerate_with_direction(date, direction)
            
        elif action == 'feedback':
            # 记录反馈
            feedback_type = kwargs.get('type', '')
            content = kwargs.get('content', '')
            return self._record_and_solidify_feedback(date, feedback_type, content)
            
        elif action == 'skip':
            # 跳过
            logger.info(f"跳过 {date} 的发布")
            return True
            
        else:
            logger.error(f"未知审核动作: {action}")
            return False
    
    def _publish_candidate(self, date: str, candidate_num: int):
        """发布指定候选"""
        candidate_file = self.base_dir / 'output' / date / f'candidate_{candidate_num}.md'
        
        if not candidate_file.exists():
            logger.error(f"候选文件不存在: {candidate_file}")
            return False
        
        # 调用wechat-publisher发布
        try:
            result = subprocess.run(
                ['wenyan', 'publish', '-f', str(candidate_file), '-t', 'lapis', '-h', 'solarized-light'],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, 'WECHAT_APP_ID': self.secrets['wechat']['app_id'], 'WECHAT_APP_SECRET': self.secrets['wechat']['app_secret']}
            )
            
            if '上传成功' in result.stdout:
                logger.info(f"✅ 候选 {candidate_num} 已发布到草稿箱")
                return True
            else:
                logger.error(f"发布失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"发布异常: {e}")
            return False
    
    def _regenerate_with_direction(self, date: str, direction: str):
        """按新方向重新生成"""
        logger.info(f"按方向重新生成: {direction}")
        
        # 记录到反馈系统
        self.solidifier.record_feedback(
            article_id=date,
            stage='重新生成',
            feedback_type='内容方向',
            content=f'用户要求重新生成，方向: {direction}',
            severity='medium'
        )
        
        # 重新运行生成流程
        return self.run_multi_candidate_workflow()
    
    def _record_and_solidify_feedback(self, date: str, feedback_type: str, content: str):
        """记录并固化反馈"""
        logger.info(f"记录反馈: {feedback_type}")
        
        # 记录到数据库
        # TODO: 从数据库获取article_id
        
        # 固化到系统
        self.solidifier.record_feedback(
            article_id=date,
            stage='初稿审核',
            feedback_type=feedback_type,
            content=content
        )
        
        logger.info("✅ 反馈已记录并固化")
        return True
    
    def generate_feedback_report(self, days: int = 7):
        """生成反馈报告"""
        report = self.solidifier.generate_feedback_report(days)
        print(report)
        return report

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced Content Pipeline')
    parser.add_argument('--run', action='store_true', help='运行多候选生成')
    parser.add_argument('--select', type=str, help='选择候选发布 (日期)')
    parser.add_argument('--candidate', type=int, default=1, help='候选编号')
    parser.add_argument('--regenerate', type=str, help='重新生成 (日期)')
    parser.add_argument('--direction', type=str, help='重新生成方向')
    parser.add_argument('--feedback', type=str, help='记录反馈 (日期)')
    parser.add_argument('--type', type=str, help='反馈类型')
    parser.add_argument('--content', type=str, help='反馈内容')
    parser.add_argument('--report', action='store_true', help='生成反馈报告')
    parser.add_argument('--days', type=int, default=7, help='报告天数')
    parser.add_argument('--check-mail', action='store_true', help='检查邮件回复')
    
    args = parser.parse_args()
    
    pipeline = AdvancedContentPipeline()
    
    if args.run:
        success = pipeline.run_multi_candidate_workflow(count=3)
        sys.exit(0 if success else 1)
        
    elif args.select:
        success = pipeline.process_review(
            args.select, 'select', candidate_num=args.candidate
        )
        sys.exit(0 if success else 1)
        
    elif args.regenerate:
        success = pipeline.process_review(
            args.regenerate, 'regenerate', direction=args.direction or ''
        )
        sys.exit(0 if success else 1)
        
    elif args.feedback:
        success = pipeline.process_review(
            args.feedback, 'feedback', type=args.type, content=args.content
        )
        sys.exit(0 if success else 1)
        
    elif args.report:
        pipeline.generate_feedback_report(args.days)
        
    elif args.check_mail:
        # 检查邮件回复
        logger.info("检查邮件回复...")
        emails = pipeline.review_mail.check_new_emails()
        
        for email in emails:
            if pipeline.review_mail.is_review_reply(email):
                logger.info(f"收到审核回复: {email.get('subject', '')}")
                instruction = pipeline.review_mail.parse_instruction(email.get('body', ''))
                logger.info(f"解析指令: {instruction}")
                
    else:
        # 默认运行
        success = pipeline.run_multi_candidate_workflow(count=3)
        sys.exit(0 if success else 1)
