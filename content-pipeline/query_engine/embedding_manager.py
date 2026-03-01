"""
向量嵌入管理器 - OpenAI协议版
支持自定义base URL，兼容国产模型（千问、DeepSeek等）
"""

import sqlite3
import json
import os
import hashlib
from typing import List, Dict, Optional

class EmbeddingManager:
    """向量嵌入管理 - 支持OpenAI标准协议"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'article_library', 'library.db')
        self.db_path = db_path
        
        # OpenAI 配置
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
        self.dimensions = int(os.getenv('EMBEDDING_DIM', '1536'))
    
    def _generate_openai_embedding(self, text: str) -> Optional[List[float]]:
        """
        使用OpenAI标准API生成向量
        支持自定义base_url，兼容国产模型
        """
        try:
            from openai import OpenAI
            
            # 初始化客户端，支持自定义base_url
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            # 调用embedding API
            dimensions = None
            # OpenAI 的 text-embedding-3-* 支持可选 dimensions；大多数国产/开源 embedding 不支持该参数
            if self.model.startswith("text-embedding-3-"):
                dimensions = self.dimensions

            response = client.embeddings.create(
                input=text[:8192],  # 限制输入长度
                model=self.model,
                dimensions=dimensions,
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            print(f"OpenAI embedding失败: {e}")
            return None
    
    def _generate_simple_embedding(self, text: str, dim: int = 128) -> List[float]:
        """
        基于关键词的哈希向量（降级方案）
        """
        text = text.lower()
        words = text.split()
        
        vector = [0.0] * dim
        
        for i, word in enumerate(words[:100]):
            hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = hash_val % dim
            weight = 1.0 / (i + 1)
            vector[idx] += weight
        
        norm = sum(x**2 for x in vector) ** 0.5
        if norm > 0:
            vector = [x / norm for x in vector]
        
        return vector
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        生成向量，优先使用OpenAI API，失败则回退到哈希向量
        """
        # 如果有配置API key，尝试用OpenAI
        if self.api_key:
            embedding = self._generate_openai_embedding(text)
            if embedding:
                return embedding
            print("OpenAI embedding失败，回退到本地哈希向量")
        
        # 降级到哈希向量
        return self._generate_simple_embedding(text)
    
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
            
            embedding = self.generate_embedding(combined_text)
            
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
        """为所有缺失向量(embedding 为空)的文章生成向量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT article_id FROM articles
            WHERE (embedding IS NULL OR embedding = '')
              AND status = 'reviewed_approved'
            """
        )

        article_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return self._generate_embeddings_for_article_ids(article_ids)

    def regenerate_all_embeddings(self) -> Dict:
        """为库内所有文章重新生成向量（用于从伪向量迁移到真实 embedding）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT article_id FROM articles
            WHERE status = 'reviewed_approved'
            """
        )

        article_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return self._generate_embeddings_for_article_ids(article_ids)

    def _generate_embeddings_for_article_ids(self, article_ids: List[str]) -> Dict:
        """内部：按 article_id 列表生成向量"""
        print(f"需要生成 {len(article_ids)} 篇文章的向量")
        print(f"使用模型: {self.model}")
        print(f"API地址: {self.base_url}")

        success = 0
        for i, article_id in enumerate(article_ids, 1):
            if i % 10 == 0:
                print(f"进度: {i}/{len(article_ids)}")
            if self.generate_and_save_article_embedding(article_id):
                success += 1

        return {"total": len(article_ids), "success": success}
    
    def search_by_vector(
        self,
        query_text: str,
        top_k: int = 20,
        statuses: List[str] = None,
        push_statuses: List[str] = None,
        article_ids: List[str] = None,
    ) -> List[Dict]:
        """基于向量相似度搜索文章"""
        query_embedding = self.generate_embedding(query_text)

        if statuses is None:
            statuses = ["reviewed_approved"]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        status_q = ",".join(["?"] * len(statuses))
        where = f"embedding IS NOT NULL AND embedding != '' AND status IN ({status_q})"
        params = list(statuses)
        if push_statuses:
            push_q = ",".join(["?"] * len(push_statuses))
            where += f" AND push_status IN ({push_q})"
            params.extend(push_statuses)

        if article_ids:
            user_q = ",".join(["?"] * len(article_ids))
            where += f" AND article_id IN ({user_q})"
            params.extend(article_ids)

        cursor.execute(
            f"""
            SELECT article_id, title, content, topic, angle_type, quality_score, embedding
            FROM articles
            WHERE {where}
            """,
            params,
        )
        
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
    
    def batch_generate_embeddings(self, article_ids: List[str], batch_size: int = 10) -> Dict:
        """批量生成向量（用于OpenAI API批量处理）"""
        print(f"批量生成 {len(article_ids)} 篇文章的向量")
        
        success = 0
        failed = []
        
        for i in range(0, len(article_ids), batch_size):
            batch = article_ids[i:i+batch_size]
            print(f"处理批次 {i//batch_size + 1}/{(len(article_ids)-1)//batch_size + 1}")
            
            for article_id in batch:
                if self.generate_and_save_article_embedding(article_id):
                    success += 1
                else:
                    failed.append(article_id)
        
        return {"total": len(article_ids), "success": success, "failed": failed}


def generate_all_embeddings(mode: str = "missing"):
    """生成向量

    mode:
      - missing: 仅生成缺失向量的文章
      - all: 重新生成库内所有文章的向量
    """
    manager = EmbeddingManager()

    # 检查配置
    if not manager.api_key:
        print("警告: 未设置 OPENAI_API_KEY，将使用本地哈希向量")
        print("如需使用OpenAI API，请设置环境变量:")
        print("  export OPENAI_API_KEY=your_key")
        print("  export OPENAI_BASE_URL=https://api.openai.com/v1  # 或国产模型地址")
        print("  export EMBEDDING_MODEL=...  # embedding 模型")

    if mode == "all":
        return manager.regenerate_all_embeddings()
    return manager.generate_all_missing_embeddings()


def search_similar_articles(query: str, top_k: int = 5):
    """搜索相似文章"""
    manager = EmbeddingManager()
    return manager.search_by_vector(query, top_k)


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] in ('generate', 'regenerate'):
        mode = 'all' if sys.argv[1] == 'regenerate' else 'missing'
        result = generate_all_embeddings(mode)
        print(f"\n完成: 共{result['total']}篇，成功{result['success']}篇")
    else:
        results = search_similar_articles("客户经营技巧", 5)
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['title'][:40]}... (相似度: {r['vector_similarity']:.3f})")
