#!/usr/bin/env python3
"""
智能文章检索引擎
支持语义相似度匹配、多轮召回筛选
"""

import json
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import hashlib
import re

class ArticleSearchEngine:
    """文章检索引擎 - 召回+筛选策略"""
    
    def __init__(self, library=None):
        if library is None:
            # 延迟导入避免循环依赖
            from article_library.library import ArticleLibrary
            self.library = ArticleLibrary()
        else:
            self.library = library
        
        self.db_path = self.library.db_path
        self._init_search_tables()
    
    def _init_search_tables(self):
        """初始化搜索相关表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 文章语义向量表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS article_vectors (
                    article_id TEXT PRIMARY KEY,
                    embedding TEXT,  -- JSON格式存储向量
                    keywords TEXT,   -- JSON格式存储关键词
                    topic_vector TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles(article_id)
                )
            ''')
            
            # 使用统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id TEXT NOT NULL,
                    query_text TEXT,
                    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_feedback TEXT,  -- 'satisfied', 'unsatisfied', 'modified'
                    usage_count INTEGER DEFAULT 1,
                    last_used TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles(article_id)
                )
            ''')
            
            # 用户偏好表（用户明确设置）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pref_type TEXT NOT NULL,  -- 'style', 'angle', 'topic', 'length'
                    pref_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简单实现，可用jieba优化）"""
        # 停用词
        stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        
        # 简单分词（按非中文字符分割）
        words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
        
        # 统计词频
        word_freq = {}
        for word in words:
            if len(word) >= 2 and word not in stopwords:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 返回高频词
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w[0] for w in sorted_words[:10]]
    
    def _simple_embedding(self, text: str) -> List[float]:
        """
        简化的语义向量生成
        实际应用应该用OpenAI/Moonshot的embedding API
        这里用关键词hash作为简化方案
        """
        keywords = self._extract_keywords(text)
        
        # 创建一个128维的简单向量
        vector = [0.0] * 128
        for kw in keywords:
            # 用hash值影响向量
            hash_val = int(hashlib.md5(kw.encode()).hexdigest(), 16)
            for i in range(128):
                if (hash_val >> (i % 32)) & 1:
                    vector[i] += 1.0
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        if len(v1) != len(v2):
            return 0.0
        
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot / (norm1 * norm2)
    
    def index_article(self, article_id: str, content: str, topic: str, angle: str = None):
        """
        为文章建立索引（提取向量、关键词）
        
        Args:
            article_id: 文章ID
            content: 文章内容
            topic: 主题
            angle: 角度
        """
        # 组合文本用于向量化
        combined_text = f"{topic} {angle or ''} {content[:500]}"
        
        # 生成向量
        embedding = self._simple_embedding(combined_text)
        topic_vector = self._simple_embedding(topic)
        
        # 提取关键词
        keywords = self._extract_keywords(content[:1000])
        
        # 保存到数据库
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO article_vectors 
                (article_id, embedding, keywords, topic_vector, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                article_id,
                json.dumps(embedding),
                json.dumps(keywords),
                json.dumps(topic_vector),
                datetime.now().isoformat()
            ))
            conn.commit()
        
        return {
            'keywords': keywords,
            'embedding_sample': embedding[:5]
        }
    
    def _recall_candidates(self, query: str, min_quality: float = 7.0) -> List[Dict]:
        """
        第一轮召回：快速获取相关候选
        
        策略：
        1. 只查审核通过的文章
        2. 主题关键词匹配
        3. 质量分门槛
        """
        # 提取查询关键词
        query_keywords = self._extract_keywords(query)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取所有审核通过的文章
            cursor.execute('''
                SELECT a.*, av.keywords, av.embedding 
                FROM articles a
                LEFT JOIN article_vectors av ON a.article_id = av.article_id
                WHERE a.status = 'reviewed_approved'
                AND a.quality_score >= ?
                ORDER BY a.created_at DESC
                LIMIT 100
            ''', (min_quality,))
            
            candidates = []
            for row in cursor.fetchall():
                article = dict(row)
                
                # 计算关键词匹配分数
                if article.get('keywords'):
                    try:
                        article_keywords = json.loads(article['keywords'])
                        keyword_match = len(set(query_keywords) & set(article_keywords))
                    except:
                        keyword_match = 0
                else:
                    keyword_match = 0
                
                article['recall_score'] = keyword_match
                candidates.append(article)
            
            # 按召回分数排序，取前20
            candidates.sort(key=lambda x: x['recall_score'], reverse=True)
            return candidates[:20]
    
    def _rank_candidates(self, candidates: List[Dict], query: str, 
                         query_vector: List[float] = None) -> List[Dict]:
        """
        第二轮筛选：精排，选出最合适的3条
        
        排序因子：
        1. 语义相似度（权重40%）
        2. 质量分（权重25%）
        3. 使用次数（权重15%，避免过度使用）
        4. 新鲜度（权重20%）
        """
        if not candidates:
            return []
        
        # 生成查询向量（如果没有提供）
        if query_vector is None:
            query_vector = self._simple_embedding(query)
        
        now = datetime.now()
        
        # 获取使用统计
        article_ids = [c['article_id'] for c in candidates]
        usage_data = self._get_usage_stats(article_ids)
        
        ranked = []
        for article in candidates:
            # 语义相似度
            if article.get('embedding'):
                try:
                    article_vector = json.loads(article['embedding'])
                    semantic_score = self._cosine_similarity(query_vector, article_vector)
                except:
                    semantic_score = 0.3
            else:
                semantic_score = 0.3
            
            # 质量分（归一化到0-1）
            quality_score = (article.get('quality_score') or 7.0) / 10.0
            
            # 使用次数（越少越好，避免重复）
            usage_count = usage_data.get(article['article_id'], 0)
            usage_score = max(0, 1 - usage_count / 10)  # 使用10次以上降为0
            
            # 新鲜度
            try:
                created = datetime.fromisoformat(article['created_at'].replace('Z', '+00:00'))
                days_old = (now - created).days
                freshness_score = max(0, 1 - days_old / 30)  # 30天后降为0
            except:
                freshness_score = 0.5
            
            # 综合分数
            total_score = (
                semantic_score * 0.40 +
                quality_score * 0.25 +
                usage_score * 0.15 +
                freshness_score * 0.20
            )
            
            article['rank_score'] = total_score
            article['detail_scores'] = {
                'semantic': round(semantic_score, 3),
                'quality': round(quality_score, 3),
                'usage': round(usage_score, 3),
                'freshness': round(freshness_score, 3)
            }
            ranked.append(article)
        
        # 按综合分数排序，取前3
        ranked.sort(key=lambda x: x['rank_score'], reverse=True)
        return ranked[:3]
    
    def _get_usage_stats(self, article_ids: List[str]) -> Dict[str, int]:
        """获取文章使用次数统计"""
        if not article_ids:
            return {}
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in article_ids])
            cursor.execute(f'''
                SELECT article_id, SUM(usage_count) as total
                FROM usage_stats
                WHERE article_id IN ({placeholders})
                GROUP BY article_id
            ''', article_ids)
            
            return {row[0]: row[1] for row in cursor.fetchall()}
    
    def search(self, query: str, min_quality: float = 7.0) -> Optional[Dict]:
        """
        智能检索文章
        
        流程：召回 → 筛选Top3 → 随机选1
        
        Args:
            query: 用户查询
            min_quality: 最低质量分
            
        Returns:
            匹配的文章，或None
        """
        import random
        
        print(f"\n🔍 检索文章: '{query[:50]}...'" if len(query) > 50 else f"\n🔍 检索文章: '{query}'")
        
        # 第一轮：召回
        print("  Step 1: 召回候选...")
        candidates = self._recall_candidates(query, min_quality)
        print(f"    召回 {len(candidates)} 篇候选")
        
        if not candidates:
            print("    无候选，需要生成新文章")
            return None
        
        # 第二轮：精排
        print("  Step 2: 精排筛选...")
        top3 = self._rank_candidates(candidates, query)
        print(f"    选出 Top {len(top3)}")
        
        for i, art in enumerate(top3, 1):
            print(f"      {i}. {art['title'][:30]}... (score: {art['rank_score']:.3f})")
        
        # 第三轮：随机选1
        print("  Step 3: 随机选择...")
        selected = random.choice(top3)
        print(f"    选中: {selected['title'][:40]}...")
        
        # 记录使用
        self._record_usage(selected['article_id'], query)
        
        return selected
    
    def _record_usage(self, article_id: str, query: str):
        """记录文章使用"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO usage_stats (article_id, query_text, last_used)
                VALUES (?, ?, ?)
            ''', (article_id, query, datetime.now().isoformat()))
            conn.commit()
    
    def record_feedback(self, article_id: str, feedback: str):
        """
        记录用户反馈
        
        Args:
            article_id: 文章ID
            feedback: 'satisfied', 'unsatisfied', 'modified'
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE usage_stats 
                SET user_feedback = ?
                WHERE article_id = ? AND user_feedback IS NULL
                ORDER BY matched_at DESC
                LIMIT 1
            ''', (feedback, article_id))
            conn.commit()
        
        print(f"✅ 已记录反馈: {feedback}")
    
    def add_user_preference(self, pref_type: str, pref_value: str):
        """
        添加用户明确设置的偏好
        
        Args:
            pref_type: 'style', 'angle', 'topic', 'length'
            pref_value: 偏好值
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_preferences (pref_type, pref_value)
                VALUES (?, ?)
            ''', (pref_type, pref_value))
            conn.commit()
        
        print(f"✅ 已记录偏好: {pref_type} = {pref_value}")
    
    def get_search_stats(self) -> Dict:
        """获取搜索统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 总查询次数
            cursor.execute('SELECT COUNT(*) FROM usage_stats')
            total_queries = cursor.fetchone()[0]
            
            # 满意度统计
            cursor.execute('''
                SELECT user_feedback, COUNT(*) 
                FROM usage_stats 
                WHERE user_feedback IS NOT NULL
                GROUP BY user_feedback
            ''')
            feedback_stats = dict(cursor.fetchall())
            
            # 高频查询
            cursor.execute('''
                SELECT query_text, COUNT(*) as cnt
                FROM usage_stats
                GROUP BY query_text
                ORDER BY cnt DESC
                LIMIT 10
            ''')
            top_queries = cursor.fetchall()
            
            return {
                'total_queries': total_queries,
                'feedback': feedback_stats,
                'top_queries': top_queries
            }


# 便捷函数
def search_article(query: str, min_quality: float = 7.0) -> Optional[Dict]:
    """便捷搜索函数"""
    engine = ArticleSearchEngine()
    return engine.search(query, min_quality)


if __name__ == '__main__':
    # 测试
    print("🧪 测试文章检索引擎")
    
    engine = ArticleSearchEngine()
    
    # 测试索引文章
    print("\n--- 测试索引 ---")
    result = engine.index_article(
        article_id="test_001",
        content="这是一篇关于AI学习方法的文章，讲述了如何在AI时代高效学习。",
        topic="AI学习方法论",
        angle="实战派"
    )
    print(f"关键词: {result['keywords']}")
    
    # 测试搜索
    print("\n--- 测试搜索 ---")
    result = engine.search("AI学习")
    if result:
        print(f"找到文章: {result['title']}")
    else:
        print("未找到匹配文章")
    
    print("\n✅ 测试完成")
