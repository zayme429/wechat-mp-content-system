#!/usr/bin/env python3
"""
微信公众号文章管理库
统一管理所有生成的候选文章，支持审核状态标记
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import hashlib
import re

class ArticleLibrary:
    """文章管理库"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            self.base_path = Path('/root/.openclaw/workspace/content-pipeline/article_library')
            self.base_path.mkdir(exist_ok=True)
            db_path = self.base_path / 'library.db'
        else:
            self.base_path = Path(db_path).parent
            self.base_path.mkdir(exist_ok=True)
            
        self.db_path = str(db_path)
        self.articles_path = self.base_path / 'articles'
        self.articles_path.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 文章表 - 存储所有候选和正式文章
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    angle TEXT,
                    content TEXT NOT NULL,
                    word_count INTEGER,
                    candidate_num INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'candidate',
                    quality_score REAL,
                    review_result TEXT,
                    review_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    file_path TEXT,
                    share_token TEXT UNIQUE
                )
            ''')
            
            # 审核记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS review_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    notes TEXT,
                    performed_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles(article_id)
                )
            ''')
            
            # 主题统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topic_stats (
                    topic TEXT PRIMARY KEY,
                    article_count INTEGER DEFAULT 0,
                    passed_count INTEGER DEFAULT 0,
                    last_created TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def _generate_id(self, topic: str, date_str: str = None) -> str:
        """生成文章唯一ID"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        topic_slug = re.sub(r'[^\w\s]', '', topic)[:20].strip().replace(' ', '_')
        hash_suffix = hashlib.md5(f"{topic}{datetime.now()}".encode()).hexdigest()[:6]
        return f"{date_str}_{topic_slug}_{hash_suffix}"
    
    def _generate_share_token(self) -> str:
        """生成分享token"""
        return hashlib.md5(f"share{datetime.now()}".encode()).hexdigest()[:12]
    
    def save_candidate(self, title: str, topic: str, content: str, 
                       candidate_num: int, angle: str = None,
                       quality_score: float = None,
                       generation_path: str = None,
                       source_info: str = None,
                       angle_type: str = None) -> str:
        """
        保存候选文章
        
        Args:
            title: 文章标题
            topic: 主题
            content: 文章内容（Markdown）
            candidate_num: 候选编号（1/2/3）
            angle: 文章角度描述
            quality_score: 质量评分
            generation_path: 生成路径/流程
            source_info: 来源信息
            angle_type: 角度类型（如：故事案例派、话术实战派等）
            
        Returns:
            article_id: 文章唯一ID
        """
        article_id = self._generate_id(topic)
        share_token = self._generate_share_token()
        word_count = len(content)
        
        # 构建溯源信息
        if not generation_path:
            generation_path = f"主题确定 → 角度选择({angle_type or '默认'}) → 文章生成 → 质量评估"
        if not source_info:
            source_info = f"AI生成 | 候选{candidate_num} | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # 保存Markdown文件
        file_name = f"{article_id}.md"
        file_path = self.articles_path / file_name
        
        # 添加元数据头部（包含溯源信息）
        md_content = f"""---
article_id: {article_id}
title: {title}
topic: {topic}
angle: {angle or ''}
angle_type: {angle_type or ''}
candidate_num: {candidate_num}
status: candidate
quality_score: {quality_score or 0}
generation_path: {generation_path}
source_info: {source_info}
created_at: {datetime.now().isoformat()}
---

{content}
"""
        file_path.write_text(md_content, encoding='utf-8')
        
        # 保存到数据库
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO articles 
                (article_id, title, topic, angle, content, word_count, 
                 candidate_num, status, quality_score, file_path, share_token,
                 generation_path, source_info, angle_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (article_id, title, topic, angle, content, word_count,
                  candidate_num, 'candidate', quality_score, str(file_path), share_token,
                  generation_path, source_info, angle_type))
            
            # 更新主题统计
            cursor.execute('''
                INSERT INTO topic_stats (topic, article_count, last_created)
                VALUES (?, 1, ?)
                ON CONFLICT(topic) DO UPDATE SET
                article_count = article_count + 1,
                last_created = ?
            ''', (topic, datetime.now().isoformat(), datetime.now().isoformat()))
            
            conn.commit()
        
        return article_id
    
    def save_candidates_batch(self, topic: str, candidates: List[Dict]) -> List[str]:
        """
        批量保存多个候选文章
        
        Args:
            topic: 主题
            candidates: 候选列表，每个候选包含title/content/angle等
            
        Returns:
            article_ids: 文章ID列表
        """
        article_ids = []
        for i, candidate in enumerate(candidates, 1):
            article_id = self.save_candidate(
                title=candidate.get('title', f'{topic} - 候选{i}'),
                topic=topic,
                content=candidate.get('content', ''),
                candidate_num=i,
                angle=candidate.get('angle'),
                quality_score=candidate.get('quality_score')
            )
            article_ids.append(article_id)
        return article_ids
    
    def mark_reviewed(self, article_id: str, result: str, notes: str = None,
                      performed_by: str = 'system') -> bool:
        """
        标记文章审核状态
        
        Args:
            article_id: 文章ID
            result: 审核结果 - 'approved'/'rejected'/'revision_needed'
            notes: 审核备注
            performed_by: 审核人
            
        Returns:
            bool: 是否成功
        """
        valid_results = ['approved', 'rejected', 'revision_needed']
        if result not in valid_results:
            raise ValueError(f"result必须是其中之一: {valid_results}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 更新文章状态
            cursor.execute('''
                UPDATE articles 
                SET status = ?, review_result = ?, review_notes = ?, reviewed_at = ?
                WHERE article_id = ?
            ''', (f'reviewed_{result}', result, notes, datetime.now().isoformat(), article_id))
            
            if cursor.rowcount == 0:
                return False
            
            # 记录审核历史
            cursor.execute('''
                INSERT INTO review_history (article_id, action, notes, performed_by)
                VALUES (?, ?, ?, ?)
            ''', (article_id, result, notes, performed_by))
            
            # 如果审核通过，更新主题统计
            if result == 'approved':
                cursor.execute('''
                    SELECT topic FROM articles WHERE article_id = ?
                ''', (article_id,))
                topic = cursor.fetchone()[0]
                cursor.execute('''
                    UPDATE topic_stats 
                    SET passed_count = passed_count + 1
                    WHERE topic = ?
                ''', (topic,))
            
            conn.commit()
        
        return True
    
    def get_article(self, article_id: str) -> Optional[Dict]:
        """获取单篇文章详情"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM articles WHERE article_id = ?
            ''', (article_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_article_by_token(self, share_token: str) -> Optional[Dict]:
        """通过分享token获取文章"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM articles WHERE share_token = ?
            ''', (share_token,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def list_articles(self, status: str = None, topic: str = None, 
                      limit: int = 50) -> List[Dict]:
        """
        列出文章
        
        Args:
            status: 状态筛选 - 'candidate'/'reviewed_approved'/'reviewed_rejected'等
            topic: 主题筛选
            limit: 返回数量限制
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM articles WHERE 1=1'
            params = []
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            if topic:
                query += ' AND topic = ?'
                params.append(topic)
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_library_stats(self) -> Dict:
        """获取文章库统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 总体统计
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'candidate' THEN 1 ELSE 0 END) as candidates,
                    SUM(CASE WHEN status = 'reviewed_approved' THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN status = 'reviewed_rejected' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN status LIKE 'reviewed_%' THEN 1 ELSE 0 END) as total_reviewed
                FROM articles
            ''')
            row = cursor.fetchone()
            stats = {
                'total': row[0],
                'candidates': row[1],
                'approved': row[2],
                'rejected': row[3],
                'total_reviewed': row[4]
            }
            
            # 主题统计
            cursor.execute('SELECT * FROM topic_stats ORDER BY article_count DESC')
            columns = ['topic', 'article_count', 'passed_count', 'last_created']
            stats['topics'] = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return stats
    
    def get_share_link(self, article_id: str, base_url: str = None) -> Optional[str]:
        """获取文章分享链接"""
        if base_url is None:
            base_url = 'http://154.9.252.35:8080'
        
        article = self.get_article(article_id)
        if article and article.get('share_token'):
            return f"{base_url}/article/{article['share_token']}"
        return None
    
    def get_library_link(self, base_url: str = None) -> str:
        """获取文章库访问链接"""
        if base_url is None:
            base_url = 'http://154.9.252.35:8080'
        return f"{base_url}/library"
    
    def update_push_status(self, article_id: str, push_status: str, 
                           media_id: str = None, log: str = None) -> bool:
        """
        更新推送状态
        
        Args:
            article_id: 文章ID
            push_status: 推送状态 - 'article_library'/'draft_box'/'official_published'
            media_id: 微信Media ID（可选）
            log: 推送日志（可选）
        """
        valid_status = ['article_library', 'draft_box', 'official_published']
        if push_status not in valid_status:
            raise ValueError(f"push_status必须是其中之一: {valid_status}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 构建更新SQL
            sql = "UPDATE articles SET push_status = ?"
            params = [push_status]
            
            if media_id:
                sql += ", draft_media_id = ?"
                params.append(media_id)
            
            if log:
                sql += ", draft_push_log = ?"
                params.append(log)
            
            sql += ", draft_pushed_at = ? WHERE article_id = ?"
            params.extend([datetime.now().isoformat(), article_id])
            
            cursor.execute(sql, params)
            conn.commit()
            
            return cursor.rowcount > 0
    
    def revert_to_library(self, article_id: str, reason: str = "草稿被删除") -> bool:
        """
        回退到文章库状态（当草稿被删除时）
        
        Args:
            article_id: 文章ID
            reason: 回退原因
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE articles 
                SET push_status = 'article_library',
                    draft_push_log = ?,
                    draft_checked_at = ?
                WHERE article_id = ?
            ''', (f"回退到文章库: {reason}", datetime.now().isoformat(), article_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_push_status_stats(self) -> Dict:
        """获取推送状态统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    push_status,
                    COUNT(*) as count
                FROM articles
                GROUP BY push_status
            ''')
            
            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = row[1]
            
            return stats


if __name__ == '__main__':
    # 测试
    lib = ArticleLibrary()
    print("✅ 文章管理库初始化完成")
    print(f"数据库路径: {lib.db_path}")
    print(f"文章存储路径: {lib.articles_path}")
    
    # 测试保存候选
    test_candidates = [
        {
            'title': 'AI时代的学习革命：从被动接受到主动构建',
            'content': '# 测试文章\n\n这是一篇测试文章的内容...',
            'angle': '强调学习方式的转变',
            'quality_score': 8.5
        },
        {
            'title': '认知升级：AI如何重塑我们的思维模式',
            'content': '# 测试文章2\n\n这是另一篇测试文章...',
            'angle': '聚焦认知层面的影响',
            'quality_score': 7.8
        }
    ]
    
    article_ids = lib.save_candidates_batch('AI学习方法论', test_candidates)
    print(f"✅ 保存了 {len(article_ids)} 篇候选文章")
    for aid in article_ids:
        print(f"  - {aid}")
        print(f"    分享链接: {lib.get_share_link(aid)}")
    
    # 测试标记审核
    lib.mark_reviewed(article_ids[0], 'approved', '内容质量不错，角度新颖')
    print(f"✅ 标记文章 {article_ids[0]} 审核通过")
    
    # 查看统计
    stats = lib.get_library_stats()
    print(f"\n文章库统计:")
    print(f"  总数: {stats['total']}")
    print(f"  候选: {stats['candidates']}")
    print(f"  审核通过: {stats['approved']}")
    
    print(f"\n📚 文章库访问链接: {lib.get_library_link()}")
