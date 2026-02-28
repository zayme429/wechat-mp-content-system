"""
向量嵌入管理器 - 简化版
为文章生成语义向量，支持向量相似度搜索
"""

import sqlite3
import json
import os
import hashlib
from typing import List, Dict

class EmbeddingManager:
    """向量嵌入管理"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'article_library', 'library.db')
        self.db_path = db_path
    
    def _generate_simple_embedding(self, text: str, dim: int = 128) -> List[float]:
        """
        基于关键词的哈希向量
        简单但有效，不依赖外部API
        """
        # 文本预处理
        text = text.lower()
        words = text.split()
        
        # 初始化向量
        vector = [0.0] * dim
        
        # 基于关键词生成向量
        for i, word in enumerate(words[:100]):
            hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = hash_val % dim
            weight = 1.0 / (i + 1)
            vector[idx] += weight
        
        # 归一化
        norm = sum(x**2 for x in vector) ** 0.5
        if norm > 0:
            vector = [x / norm for x in vector]
        
        return vector
    
    def generate_and_save_article_embedding(self, article_id: str) -> bool:
        """为单篇文章生成并保存向量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT title, content, topic, angle_type
                FROM articles WHERE article_id = ?
            """, (article_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            title, content, topic, angle_type = row
            combined_text = f"{title}\n{title}\n主题：{topic}\n角度：{angle_type}\n{content[:500]}"
            
            embedding = self._generate_simple_embedding(combined_text)
            
            cursor.execute("""
                UPDATE articles SET embedding = ? WHERE article_id = ?
            """, (json.dumps(embedding), article_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"生成失败 {article_id}: {e}")
            return False
    
    def generate_all_missing_embeddings(self) -> Dict:
        """为所有没有向量的文章生成向量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT article_id FROM articles 
            WHERE embedding IS NULL OR embedding = ''
        """)
        
        article_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"需要生成 {len(article_ids)} 篇文章的向量")
        
        success = 0
        for i, article_id in enumerate(article_ids, 1):
            if i % 10 == 0:
                print(f"进度: {i}/{len(article_ids)}")
            if self.generate_and_save_article_embedding(article_id):
                success += 1
        
        return {"total": len(article_ids), "success": success}
    
    def search_by_vector(self, query_text: str, top_k: int = 10) -> List[Dict]:
        """基于向量相似度搜索文章"""
        query_embedding = self._generate_simple_embedding(query_text)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 放宽条件：只要有向量的候选文章都可以搜索
        cursor.execute("""
            SELECT article_id, title, content, topic, angle_type, quality_score, embedding
            FROM articles 
            WHERE embedding IS NOT NULL AND embedding != ''
        """)
        
        results = []
        for row in cursor.fetchall():
            article_id, title, content, topic, angle_type, quality_score, embedding_json = row
            
            try:
                article_embedding = json.loads(embedding_json)
                similarity = self._cosine_similarity(query_embedding, article_embedding)
                
                results.append({
                    "article_id": article_id,
                    "title": title,
                    "content": content,
                    "topic": topic,
                    "angle_type": angle_type,
                    "quality_score": quality_score,
                    "vector_similarity": similarity,
                    "match_score": similarity * 10
                })
            except:
                continue
        
        conn.close()
        
        results.sort(key=lambda x: x["vector_similarity"], reverse=True)
        return results[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        min_len = min(len(vec1), len(vec2))
        vec1 = vec1[:min_len]
        vec2 = vec2[:min_len]
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(a * a for a in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


def generate_all_embeddings():
    """生成所有缺失的向量"""
    manager = EmbeddingManager()
    return manager.generate_all_missing_embeddings()


def search_similar_articles(query: str, top_k: int = 5):
    """搜索相似文章"""
    manager = EmbeddingManager()
    return manager.search_by_vector(query, top_k)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'generate':
        result = generate_all_embeddings()
        print(f"\n完成: 共{result['total']}篇，成功{result['success']}篇")
    else:
        results = search_similar_articles("客户经营技巧", 5)
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['title'][:40]}... (相似度: {r['vector_similarity']:.3f})")
