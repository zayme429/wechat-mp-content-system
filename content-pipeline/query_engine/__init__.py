"""
查询推荐引擎 - 核心模块
"""

import sqlite3
import random
from typing import List, Dict, Tuple, Optional
from datetime import datetime

class QueryEngine:
    """文章查询推荐引擎"""

    def _count_library_pool(self) -> int:
        """文章池总量（用于漏斗展示）。

        用户要求：仅基于审核通过(reviewed_approved)的文章进行推荐。
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM articles
                WHERE status = 'reviewed_approved'
                """
            )
            count = cursor.fetchone()[0] or 0
            conn.close()
            return int(count)
        except Exception:
            return 0

    
    def __init__(self, db_path: str = None, config: Dict = None):
        """初始化查询引擎"""
        if db_path is None:
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'article_library', 'library.db')
        self.db_path = db_path
        
        # 加载配置
        from query_engine.config_manager import get_config
        self.config_manager = get_config()
        self.config = config or self.config_manager.get_effective_config()
        
        # 记录查询过程（用于溯源）
        self.query_trace = []
    
    def query(self, user_input: str, user_id: str = "insurance_agent", 
              custom_config: Dict = None) -> Dict:
        """主查询接口"""
        # 使用自定义配置（如果有）
        if custom_config:
            original_config = self.config
            self.config = {**self.config, **custom_config}
        
        try:
            # 清空查询追踪
            self.query_trace = []
            
            # 1. 意图识别
            intent = self._recognize_intent(user_input)
            self.query_trace.append({
                "step": "intent_recognition",
                "input": user_input,
                "output": intent
            })
            
            # 2. 召回
            recall_strategy = self.config.get("recall_strategy", "hybrid")

            library_total = self._count_library_pool()
            candidates = self._recall_by_strategy(intent, recall_strategy)
            self.query_trace.append({
                "step": "recall",
                "strategy": recall_strategy,
                "library_total": library_total,
                "candidates_count": len(candidates)
            })
            
            # 3. 筛选
            if not candidates:
                return self._build_no_match_result(intent)
            
            filter_strategy = self.config.get("filter_strategy", "top_n")
            selected, alternatives, recommend_reason = self._filter_by_strategy(
                candidates, filter_strategy, intent, user_input
            )
            self.query_trace.append({
                "step": "filter",
                "strategy": filter_strategy,
                "selected": selected["article_id"],
                "recommend_reason": recommend_reason
            })
            
            # 4. 构建结果
            result = self._build_success_result(intent, selected, alternatives, recommend_reason)
            result["query_trace"] = self.query_trace
            result["config_used"] = self.config
            
            return result
            
        finally:
            if custom_config:
                self.config = original_config
    
    def _recognize_intent(self, user_input: str) -> Dict:
        """意图识别"""
        intent = {
            "original_query": user_input,
            "topic": None,
            "audience": "保险代理人",
            "intent_type": "内容查询",
            "keywords": []
        }
        
        keywords_map = {
            "客户经营": ["客户", "经营", "维护", "跟进", "回访"],
            "保险获客": ["获客", "新客户", "转介绍", "开发客户"],
            "转介绍": ["转介绍", "推荐", "介绍客户"],
            "社群营销": ["社群", "微信群", "朋友圈"]
        }
        
        matched_keywords = []
        for topic, keywords in keywords_map.items():
            for kw in keywords:
                if kw in user_input:
                    matched_keywords.append(kw)
                    if not intent["topic"]:
                        intent["topic"] = topic
        
        intent["keywords"] = matched_keywords
        
        if not intent["topic"]:
            intent["topic"] = "保险客户经营"
            
        return intent
    
    def _recall_by_strategy(self, intent: Dict, strategy: str) -> List[Dict]:
        """根据策略召回"""
        if strategy == "topic_exact":
            return self._recall_topic_exact(intent)
        elif strategy == "keyword_fuzzy":
            return self._recall_keyword_fuzzy(intent)
        elif strategy == "semantic_vector":
            return self._recall_semantic_vector(intent)
        elif strategy == "hybrid":
            return self._recall_hybrid(intent)
        elif strategy == "quality_first":
            return self._recall_quality_first(intent)
        else:
            return self._recall_hybrid(intent)
    
    def _recall_topic_exact(self, intent: Dict) -> List[Dict]:
        """主题精确匹配"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT article_id, title, content, topic, angle_type, quality_score
            FROM articles
            WHERE status = 'reviewed_approved'
              AND topic = ?
            ORDER BY quality_score DESC
            LIMIT 20
        """, (intent["topic"],))
        
        candidates = self._format_candidates(cursor.fetchall())
        conn.close()
        return candidates
    
    def _recall_keyword_fuzzy(self, intent: Dict) -> List[Dict]:
        """关键词模糊匹配"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        keywords = intent.get("keywords", [])
        if not keywords:
            keywords = [intent["topic"]]

        like_conditions = []
        params = []
        for kw in keywords:
            like_conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{kw}%", f"%{kw}%"])

        where_clause = " OR ".join(like_conditions)

        cursor.execute(f"""
            SELECT article_id, title, content, topic, angle_type, quality_score
            FROM articles
            WHERE status = 'reviewed_approved'
              AND ({where_clause})
            ORDER BY quality_score DESC
            LIMIT 20
        """, params)
        
        candidates = self._format_candidates(cursor.fetchall())
        conn.close()
        return candidates
    
    def _recall_semantic_vector(self, intent: Dict) -> List[Dict]:
        """语义向量召回"""
        import sys
        sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')
        from query_engine.embedding_manager import EmbeddingManager
        
        # 构建查询文本
        query_text = f"{intent['original_query']} {intent['topic']} {' '.join(intent.get('keywords', []))}"
        
        # 向量搜索
        manager = EmbeddingManager(self.db_path)
        results = manager.search_by_vector(query_text, top_k=20)
        
        # 过滤低相似度的（阈值降低到0.1以保留更多候选）
        filtered = [r for r in results if r["vector_similarity"] >= 0.1]
        
        if not filtered and results:
            # 如果没有超过阈值的，返回前10个
            filtered = results[:10]
        
        return filtered
    
    def _recall_hybrid(self, intent: Dict) -> List[Dict]:
        """混合策略"""
        # 主题召回
        topic_candidates = self._recall_topic_exact(intent)
        
        # 关键词召回
        keyword_candidates = self._recall_keyword_fuzzy(intent)
        
        # 尝试语义向量召回（如果有向量数据）
        vector_candidates = []
        try:
            vector_candidates = self._recall_semantic_vector(intent)
        except:
            pass
        
        # 合并
        all_candidates = {}
        
        # 主题匹配权重 0.4
        for c in topic_candidates:
            c["match_score"] = 4.0 + c["quality_score"] * 0.3
            all_candidates[c["article_id"]] = c
        
        # 关键词匹配权重 0.3
        for c in keyword_candidates:
            if c["article_id"] in all_candidates:
                all_candidates[c["article_id"]]["match_score"] += 3.0
            else:
                c["match_score"] = 3.0 + c["quality_score"] * 0.3
                all_candidates[c["article_id"]] = c
        
        # 语义向量权重 0.3
        for c in vector_candidates:
            if c["article_id"] in all_candidates:
                all_candidates[c["article_id"]]["match_score"] += c.get("match_score", 0) * 0.3
            else:
                c["match_score"] = c.get("match_score", 0) * 0.3
                all_candidates[c["article_id"]] = c
        
        return list(all_candidates.values())
    
    def _recall_quality_first(self, intent: Dict) -> List[Dict]:
        """质量优先"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT article_id, title, content, topic, angle_type, quality_score
            FROM articles
            WHERE status = 'reviewed_approved'
              AND quality_score >= 8.0
            ORDER BY quality_score DESC
            LIMIT 20
        """)
        
        candidates = self._format_candidates(cursor.fetchall())
        conn.close()
        return candidates
    
    def _format_candidates(self, rows) -> List[Dict]:
        """格式化候选"""
        candidates = []
        for row in rows:
            article_id, title, content, topic, angle_type, quality_score = row
            candidates.append({
                "article_id": article_id,
                "title": title,
                "content": content,
                "topic": topic,
                "angle_type": angle_type,
                "quality_score": quality_score,
                "match_score": 0.0
            })
        return candidates
    
    def _filter_by_strategy(self, candidates: List[Dict], strategy: str, 
                            intent: Dict, query: str) -> Tuple[Dict, List[Dict], str]:
        """筛选策略"""
        if len(candidates) >= 2:
            # 尝试用LLM分析
            try:
                return self._filter_by_llm(candidates, intent, query)
            except Exception as e:
                print(f"LLM分析失败: {e}")
        
        # 规则筛选
        if strategy == "threshold":
            selected, alternatives = self._filter_threshold(candidates)
        elif strategy == "top_n":
            selected, alternatives = self._filter_top_n(candidates)
        elif strategy == "weighted_random":
            selected, alternatives = self._filter_weighted_random(candidates)
        else:
            selected, alternatives = self._filter_top_n(candidates)
        
        reason = f"匹配度得分：{selected.get('match_score', 0):.1f}，主题'{intent['topic']}'"
        return selected, alternatives, reason
    
    def _filter_by_llm(self, candidates: List[Dict], intent: Dict, query: str) -> Tuple[Dict, List[Dict], str]:
        """LLM分析候选"""
        import sys
        sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')
        sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline/src')
        from query_engine.prompt_manager import get_prompt_manager
        from generator.content_generator import ContentGenerator
        import json
        import re
        
        # 准备候选信息
        candidates_info = []
        for i, c in enumerate(candidates[:3], 1):
            candidates_info.append(f"""【文章{i}】ID:{c['article_id']} 标题:{c['title']} 主题:{c['topic']} 角度:{c['angle_type']} 质量:{c['quality_score']} 内容:{c['content'][:150]}...""")
        
        pm = get_prompt_manager()
        prompt = pm.render_prompt("candidate_analysis", {
            "query": query,
            "intent": json.dumps(intent, ensure_ascii=False),
            "candidate_count": len(candidates_info),
            "candidates_info": "\n".join(candidates_info)
        })
        
        generator = ContentGenerator()
        response = generator._call_llm(prompt)
        
        # 解析JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            recommended_id = result.get("recommendation", {}).get("recommended_id")
            reason = result.get("recommendation", {}).get("reason", "")
            
            for c in candidates:
                if c["article_id"] == recommended_id:
                    return c, [x for x in candidates if x["article_id"] != recommended_id][:2], f"LLM: {reason}"
        
        raise Exception("LLM解析失败")
    
    def _filter_threshold(self, candidates: List[Dict]) -> Tuple[Dict, List[Dict]]:
        """阈值过滤"""
        sorted_candidates = sorted(candidates, key=lambda x: x.get("match_score", 0), reverse=True)
        return sorted_candidates[0], sorted_candidates[1:3]
    
    def _filter_top_n(self, candidates: List[Dict]) -> Tuple[Dict, List[Dict]]:
        """Top N随机"""
        sorted_candidates = sorted(candidates, key=lambda x: x.get("match_score", 0), reverse=True)
        top3 = sorted_candidates[:3]
        selected = random.choice(top3)
        alternatives = [c for c in top3 if c["article_id"] != selected["article_id"]]
        return selected, alternatives
    
    def _filter_weighted_random(self, candidates: List[Dict]) -> Tuple[Dict, List[Dict]]:
        """加权随机"""
        weights = [c.get("match_score", 5) for c in candidates]
        total = sum(weights)
        weights = [w/total for w in weights]
        selected = random.choices(candidates, weights=weights, k=1)[0]
        alternatives = [c for c in candidates if c["article_id"] != selected["article_id"]][:2]
        return selected, alternatives
    
    def _build_no_match_result(self, intent: Dict) -> Dict:
        """无匹配"""
        return {
            "status": "no_match",
            "intent": intent,
            "message": "文章库中没有匹配的文章",
            "recommendation": None,
            "query_trace": self.query_trace
        }
    
    def _build_success_result(self, intent: Dict, selected: Dict, alternatives: List[Dict], reason: str) -> Dict:
        """成功结果"""
        push_mode = self.config.get("push_mode", "confirm")
        display_options = self.config.get("display", {})
        
        return {
            "status": "success",
            "intent": intent,
            "query_process": {
                "library_total": next((t.get("library_total", 0) for t in self.query_trace if t["step"] == "recall"), 0),
                "recall_count": next((t["candidates_count"] for t in self.query_trace if t["step"] == "recall"), 0),
                "filter_top": len(alternatives) + 1,
                "used_llm": any(t.get("step") == "filter" and "LLM" in str(t.get("recommend_reason", "")) for t in self.query_trace)
            },
            "recommendation": {
                "article_id": selected["article_id"],
                "title": selected["title"],
                "content_preview": selected["content"][:200] + "...",
                "match_score": selected.get("match_score", 0),
                "match_reason": reason,
                "score_note": "match_score=vector_similarity*10 (仅用于排序/筛选；不是推送内容)",
                "topic": selected["topic"],
                "angle_type": selected["angle_type"]
            },
            "alternatives": [{"article_id": c["article_id"], "title": c["title"], "match_score": c.get("match_score", 0)} for c in alternatives[:2]],
            "push_mode": push_mode
        }
    
    def push_to_wechat(self, article_id: str) -> Dict:
        """推送到微信"""
        import sys
        sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline/article_library')
        from web_server import push_to_wechat_draft
        
        success, message = push_to_wechat_draft(article_id)
        
        return {
            "success": success,
            "message": message,
            "article_id": article_id,
            "pushed_at": datetime.now().isoformat()
        }


def query_articles(user_input: str, user_id: str = "insurance_agent", config: Dict = None) -> Dict:
    """便捷查询"""
    engine = QueryEngine()
    return engine.query(user_input, user_id, config)
