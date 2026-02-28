#!/usr/bin/env python3
"""
高级内容管理系统
支持多候选生成、反馈固化、偏好学习
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import hashlib

class ContentDatabase:
    """内容数据库管理"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = '/root/.openclaw/workspace/content-pipeline/database/content.db'
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 文章表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    angle TEXT,
                    content TEXT NOT NULL,
                    word_count INTEGER,
                    status TEXT DEFAULT 'draft',
                    selected_candidate INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    published_at TIMESTAMP,
                    performance_score REAL
                )
            ''')
            
            # 候选文章表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER,
                    candidate_num INTEGER,
                    topic TEXT,
                    angle TEXT,
                    content TEXT,
                    uniqueness_score REAL,
                    quality_score REAL,
                    is_selected BOOLEAN DEFAULT 0,
                    FOREIGN KEY (article_id) REFERENCES articles(id)
                )
            ''')
            
            # 反馈表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER,
                    stage TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    severity TEXT DEFAULT 'medium',
                    is_addressed BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles(id)
                )
            ''')
            
            # 偏好学习表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    preference TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    last_triggered TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # 主题表现表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topic_performance (
                    topic_id TEXT PRIMARY KEY,
                    topic_name TEXT,
                    use_count INTEGER DEFAULT 0,
                    avg_score REAL,
                    last_used TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            conn.commit()
    
    def save_article(self, date: str, topic: str, content: str, 
                     candidates: List[Dict], status: str = 'draft') -> int:
        """保存文章和候选"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 保存主文章
            word_count = len(content)
            cursor.execute('''
                INSERT INTO articles (date, topic, content, word_count, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (date, topic, content, word_count, status))
            
            article_id = cursor.lastrowid
            
            # 保存候选
            for i, candidate in enumerate(candidates, 1):
                cursor.execute('''
                    INSERT INTO candidates 
                    (article_id, candidate_num, topic, angle, content, 
                     uniqueness_score, quality_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article_id, i, 
                    candidate.get('topic', topic),
                    candidate.get('angle', ''),
                    candidate.get('content', ''),
                    candidate.get('uniqueness_score', 0),
                    candidate.get('quality_score', 0)
                ))
            
            conn.commit()
            return article_id
    
    def save_feedback(self, article_id: int, stage: str, 
                     feedback_type: str, content: str, 
                     severity: str = 'medium'):
        """保存反馈"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO feedback (article_id, stage, feedback_type, content, severity)
                VALUES (?, ?, ?, ?, ?)
            ''', (article_id, stage, feedback_type, content, severity))
            conn.commit()
    
    def learn_preference(self, category: str, preference: str):
        """学习用户偏好"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute('''
                SELECT id, frequency FROM preferences 
                WHERE category = ? AND preference = ?
            ''', (category, preference))
            
            result = cursor.fetchone()
            if result:
                # 更新频率
                cursor.execute('''
                    UPDATE preferences 
                    SET frequency = frequency + 1, last_triggered = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), result[0]))
            else:
                # 新建偏好
                cursor.execute('''
                    INSERT INTO preferences (category, preference, last_triggered)
                    VALUES (?, ?, ?)
                ''', (category, preference, datetime.now().isoformat()))
            
            conn.commit()
    
    def get_active_preferences(self, category: str, min_frequency: int = 3) -> List[str]:
        """获取高频偏好"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT preference FROM preferences 
                WHERE category = ? AND frequency >= ? AND is_active = 1
                ORDER BY frequency DESC
            ''', (category, min_frequency))
            return [row[0] for row in cursor.fetchall()]
    
    def get_feedback_summary(self, days: int = 30) -> Dict:
        """获取反馈统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 各类反馈数量
            cursor.execute('''
                SELECT feedback_type, COUNT(*) FROM feedback 
                WHERE created_at >= date('now', '-{} days')
                GROUP BY feedback_type
            '''.format(days))
            type_counts = dict(cursor.fetchall())
            
            # 未解决的问题
            cursor.execute('''
                SELECT COUNT(*) FROM feedback 
                WHERE is_addressed = 0
            ''')
            unaddressed = cursor.fetchone()[0]
            
            return {
                'type_counts': type_counts,
                'unaddressed': unaddressed
            }
    
    def get_article_history(self, limit: int = 10) -> List[Dict]:
        """获取文章历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, date, topic, status, word_count, created_at
                FROM articles
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            columns = ['id', 'date', 'topic', 'status', 'word_count', 'created_at']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

if __name__ == '__main__':
    db = ContentDatabase()
    print("✅ 数据库初始化完成")
    
    # 测试
    candidates = [
        {'topic': '测试1', 'content': '内容1', 'angle': '角度1'},
        {'topic': '测试2', 'content': '内容2', 'angle': '角度2'},
        {'topic': '测试3', 'content': '内容3', 'angle': '角度3'}
    ]
    
    article_id = db.save_article('20260226', '测试主题', '主内容', candidates)
    print(f"✅ 测试文章保存，ID: {article_id}")
