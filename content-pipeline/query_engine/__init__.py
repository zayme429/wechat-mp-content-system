"""
查询推荐引擎 - 支持策略配置
提供智能文章查询和推荐功能
"""

import sqlite3
import random
from typing import List, Dict, Tuple, Optional
from datetime import datetime

class QueryEngine:
    """文章查询推荐引擎 - 可配置版本"""
    
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
        """
        主查询接口 - 支持自定义配置
        
        Args:
            user_input: 用户查询输入
            user_id: 用户ID
            custom_config: 自定义配置（覆盖默认配置）
            
        Returns:
            查询结果
        """
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
                "output": intent,
                "method": "keyword_matching"  # 可配置为LLM
            })
            
            # 2. 召回（根据配置的策略）
            recall_strategy = self.config.get("recall_strategy", "hybrid")
            candidates = self._recall_by_strategy(intent, user_id, recall_strategy)
            self.query_trace.append({
                "step": "recall",
                "strategy": recall_strategy,
                "candidates_count": len(candidates),
                "params": self.config_manager.get_strategy_params("recall", recall_strategy)
            })
            
            # 3. 筛选（根据配置的策略）
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
                "alternatives": [a["article_id"] for a in alternatives],
                "recommend_reason": recommend_reason,
                "params": self.config_manager.get_strategy_params("filter", filter_strategy)
            })
            
            # 4. 构建结果
            result = self._build_success_result(intent, selected, alternatives)
            result["query_trace"] = self.query_trace
            result["config_used"] = self.config
            
            return result
            
        finally:
            # 恢复原始配置
            if custom_config:
                self.config = original_config
    
    def _recognize_intent(self, user_input: str) -> Dict:
        """意图识别 - 使用LLM"""
        import sys
        sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')
        from query_engine.prompt_manager import get_prompt_manager
        from generator.content_generator import ContentGenerator
        
        # 使用Prompt
        pm = get_prompt_manager()
        prompt = pm.render_prompt("intent_recognition", {"query": user_input})
        
        # 调用LLM
        try:
            generator = ContentGenerator()
            response = generator._call_llm(prompt)
            
            # 解析JSON
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                intent = json.loads(json_match.group())
                intent["original_query"] = user_input
                return intent
        except Exception as e:
            print(f"LLM意图识别失败: {e}, 使用备用规则")
        
        # 备用：规则匹配
        return self._recognize_intent_fallback(user_input)
    
    def _recognize_intent_fallback(self, user_input: str) -> Dict:
        """意图识别备用（规则匹配）"""
        intent = {
            "original_query": user_input,
            "topic": None,
            "audience": "保险代理人",
            "intent_type": "内容查询",
            "keywords": [],
            "specific_requirements": ""
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
    
    def _recall_by_strategy(self, intent: Dict, user_id: str, strategy: str) -> List[Dict]:
        """根据策略召回候选"""
        params = self.config_manager.get_strategy_params("recall", strategy)
        
        if strategy == "topic_exact":
            return self._recall_topic_exact(intent, user_id, params)
        elif strategy == "keyword_fuzzy":
            return self._recall_keyword_fuzzy(intent, user_id, params)
        elif strategy == "hybrid":
            return self._recall_hybrid(intent, user_id, params)
        elif strategy == "quality_first":
            return self._recall_quality_first(intent, user_id, params)
        else:
            return self._recall_hybrid(intent, user_id, params)  # 默认混合
    
    def _recall_topic_exact(self, intent: Dict, user_id: str, params: Dict) -> List[Dict]:
        """主题精确匹配召回"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        topic = intent["topic"]
        
        cursor.execute("""
            SELECT article_id, title, content, topic, angle_type, quality_score
            FROM articles 
            WHERE user_id = ? 
              AND status = 'reviewed_approved'
              AND push_status = 'article_library'
              AND topic = ?
            ORDER BY quality_score DESC
            LIMIT 20
        """, (user_id, topic))
        
        candidates = self._format_candidates(cursor.fetchall())
        conn.close()
        return candidates
    
    def _recall_keyword_fuzzy(self, intent: Dict, user_id: str, params: Dict) -> List[Dict]:
        """关键词模糊匹配召回"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        keywords = intent.get("keywords", [])
        if not keywords:
            keywords = [intent["topic"]]
        
        # 构建模糊查询条件
        like_conditions = []
        params_list = [user_id]
        for kw in keywords:
            like_conditions.append("(title LIKE ? OR content LIKE ?)")
            params_list.extend([f"%{kw}%", f"%{kw}%"])
        
        where_clause = " OR ".join(like_conditions)
        
        cursor.execute(f"""
            SELECT article_id, title, content, topic, angle_type, quality_score
            FROM articles 
            WHERE user_id = ? 
              AND status = 'reviewed_approved'
              AND push_status = 'article_library'
              AND ({where_clause})
            ORDER BY quality_score DESC
            LIMIT 20
        """, params_list)
        
        candidates = self._format_candidates(cursor.fetchall())
        conn.close()
        return candidates
    
    def _recall_hybrid(self, intent: Dict, user_id: str, params: Dict) -> List[Dict]:
        """混合策略召回"""
        weights = params.get("weights", {"topic": 0.4, "keyword": 0.3, "semantic": 0.3})
        
        # 主题召回
        topic_candidates = self._recall_topic_exact(intent, user_id, {})
        
        # 关键词召回
        keyword_candidates = self._recall_keyword_fuzzy(intent, user_id, {})
        
        # 合并去重并计算加权分数
        all_candidates = {}
        
        for c in topic_candidates:
            c["match_score"] = weights["topic"] * 10 + c["quality_score"] * 0.3
            all_candidates[c["article_id"]] = c
        
        for c in keyword_candidates:
            if c["article_id"] in all_candidates:
                all_candidates[c["article_id"]]["match_score"] += weights["keyword"] * 10
            else:
                c["match_score"] = weights["keyword"] * 10 + c["quality_score"] * 0.3
                all_candidates[c["article_id"]] = c
        
        return list(all_candidates.values())
    
    def _recall_quality_first(self, intent: Dict, user_id: str, params: Dict) -> List[Dict]:
        """质量优先召回"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        min_quality = params.get("min_quality_score", 8.0)
        
        cursor.execute("""
            SELECT article_id, title, content, topic, angle_type, quality_score
            FROM articles 
            WHERE user_id = ? 
              AND status = 'reviewed_approved'
              AND push_status = 'article_library'
              AND quality_score >= ?
            ORDER BY quality_score DESC, created_at DESC
            LIMIT 20
        """, (user_id, min_quality))
        
        candidates = self._format_candidates(cursor.fetchall())
        conn.close()
        return candidates
    
    def _filter_by_strategy(self, candidates: List[Dict], strategy: str, 
                            intent: Dict = None, query: str = "") -> Tuple[Dict, List[Dict], str]:
        """根据策略筛选 - 支持LLM分析"""
        # 如果候选超过2篇且配置允许，使用LLM分析
        if len(candidates) >= 2 and self.config.get("use_llm_analysis", True):
            return self._filter_by_llm(candidates, intent, query)
        
        # 否则使用规则策略
        params = self.config_manager.get_strategy_params("filter", strategy)
        
        if strategy == "threshold":
            selected, alternatives = self._filter_threshold(candidates, params)
        elif strategy == "top_n":
            selected, alternatives = self._filter_top_n(candidates, params)
        elif strategy == "weighted_random":
            selected, alternatives = self._filter_weighted_random(candidates, params)
        elif strategy == "diversity":
            selected, alternatives = self._filter_diversity(candidates, params)
        else:
            selected, alternatives = self._filter_top_n(candidates, {"top_n": 3})
        
        reason = f"使用{strategy}策略筛选，匹配度得分：{selected.get('match_score', 0):.1f}"
        return selected, alternatives, reason
    
    def _filter_by_llm(self, candidates: List[Dict], intent: Dict, query: str) -> Tuple[Dict, List[Dict], str]:
        """使用LLM分析候选文章并给出推荐"""
        import sys
        sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')
        from query_engine.prompt_manager import get_prompt_manager
        from generator.content_generator import ContentGenerator
        import json
        import re
        
        try:
            # 准备候选信息
            candidates_info = []
            for i, c in enumerate(candidates[:5], 1):  # 最多分析5篇
                candidates_info.append(f"""
【文章{i}】
ID: {c['article_id']}
标题: {c['title']}
主题: {c['topic']}
角度: {c['angle_type']}
质量分: {c['quality_score']}
内容预览: {c['content'][:200]}...
""")
            
            # 使用Prompt
            pm = get_prompt_manager()
            prompt = pm.render_prompt("candidate_analysis", {
                "query": query,
                "intent": json.dumps(intent, ensure_ascii=False),
                "candidate_count": len(candidates_info),
                "candidates_info": "\n".join(candidates_info)
            })
            
            # 调用LLM
            generator = ContentGenerator()
            response = generator._call_llm(prompt)
            
            # 解析JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                analysis_result = json.loads(json_match.group())
                
                # 找到推荐的文章
                recommended_id = analysis_result.get("recommendation", {}).get("recommended_id")
                reason = analysis_result.get("recommendation", {}).get("reason", "")
                
                # 从候选中找到对应文章
                for c in candidates:
                    if c["article_id"] == recommended_id:
                        selected = c
                        alternatives = [x for x in candidates if x["article_id"] != recommended_id][:2]
                        self.query_trace.append({
                            "step": "llm_analysis",
                            "analysis": analysis_result.get("analysis", []),
                            "recommendation": analysis_result.get("recommendation", {})
                        })
                        return selected, alternatives, reason
        except Exception as e:
            print(f"LLM分析失败: {e}, 使用备用策略")
        
        # 备用：使用top_n
        selected, alternatives = self._filter_top_n(candidates, {"top_n": 3})
        return selected, alternatives, f"LLM分析失败，使用Top3随机策略。匹配度：{selected.get('match_score', 0):.1f}"
    
    def _filter_threshold(self, candidates: List[Dict], params: Dict) -> Tuple[Dict, List[Dict]]:
        """阈值过滤"""
        min_score = params.get("min_match_score", 6.0)
        filtered = [c for c in candidates if c.get("match_score", 0) >= min_score]
        
        if not filtered:
            return candidates[0], candidates[1:3] if len(candidates) > 1 else []
        
        return filtered[0], filtered[1:3] if len(filtered) > 1 else []
    
    def _filter_top_n(self, candidates: List[Dict], params: Dict) -> Tuple[Dict, List[Dict]]:
        """Top N后随机"""
        top_n = params.get("top_n", 3)
        
        # 按匹配分数排序
        sorted_candidates = sorted(candidates, key=lambda x: x.get("match_score", 0), reverse=True)
        top_candidates = sorted_candidates[:top_n]
        
        # 随机选择
        selected = random.choice(top_candidates)
        alternatives = [c for c in top_candidates if c["article_id"] != selected["article_id"]]
        
        return selected, alternatives
    
    def _filter_weighted_random(self, candidates: List[Dict], params: Dict) -> Tuple[Dict, List[Dict]]:
        """加权随机"""
        import random
        
        # 计算权重
        weights = [c.get("match_score", 5) for c in candidates]
        total = sum(weights)
        weights = [w/total for w in weights]
        
        # 加权随机选择
        selected = random.choices(candidates, weights=weights, k=1)[0]
        alternatives = [c for c in candidates if c["article_id"] != selected["article_id"]][:2]
        
        return selected, alternatives
    
    def _filter_diversity(self, candidates: List[Dict], params: Dict) -> Tuple[Dict, List[Dict]]:
        """多样性保证"""
        # 按角度分组
        by_angle = {}
        for c in candidates:
            angle = c.get("angle_type", "unknown")
            if angle not in by_angle:
                by_angle[angle] = []
            by_angle[angle].append(c)
        
        # 每个角度选最好的
        diverse_candidates = []
        for angle, articles in by_angle.items():
            best = max(articles, key=lambda x: x.get("match_score", 0))
            diverse_candidates.append(best)
        
        # 排序后选前几个
        diverse_candidates.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        return diverse_candidates[0], diverse_candidates[1:3]
    
    def _format_candidates(self, rows) -> List[Dict]:
        """格式化候选文章"""
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
    
    def _build_no_match_result(self, intent: Dict) -> Dict:
        """构建无匹配结果"""
        return {
            "status": "no_match",
            "intent": intent,
            "message": "文章库中没有匹配的文章，建议：\n1. 调整查询关键词\n2. 更换召回策略\n3. 生成新文章",
            "recommendation": None,
            "query_trace": self.query_trace,
            "config_used": self.config
        }
    
    def _build_success_result(self, intent: Dict, selected: Dict, alternatives: List[Dict]) -> Dict:
        """构建成功结果"""
        push_mode = self.config.get("push_mode", "confirm")
        display_options = self.config.get("display", {})
        
        # 获取LLM推荐理由
        recommend_reason = ""
        for trace in self.query_trace:
            if trace.get("step") == "filter" and "recommend_reason" in trace:
                recommend_reason = trace["recommend_reason"]
                break
        
        if not recommend_reason:
            recommend_reason = f"主题匹配'{intent['topic']}'，质量分{selected['quality_score']}"
        
        result = {
            "status": "success",
            "intent": intent,
            "query_process": {
                "recall_count": len([t for t in self.query_trace if t["step"] == "recall"]),
                "filter_top": len(alternatives) + 1,
                "selection_method": self.config.get("filter_strategy", "top_n"),
                "used_llm": any(t.get("step") == "llm_analysis" for t in self.query_trace)
            },
            "recommendation": {
                "article_id": selected["article_id"],
                "title": selected["title"],
                "content_preview": selected["content"][:200] + "..." if display_options.get("show_reason", True) else None,
                "match_score": selected.get("match_score", 0),
                "match_reason": recommend_reason if display_options.get("show_reason", True) else None,
                "topic": selected["topic"],
                "angle_type": selected["angle_type"]
            },
            "alternatives": [
                {
                    "article_id": c["article_id"],
                    "title": c["title"],
                    "match_score": c.get("match_score", 0)
                }
                for c in alternatives[:display_options.get("max_alternatives", 2)]
            ] if display_options.get("show_candidates", True) else [],
            "push_mode": push_mode,
            "actions_available": self._get_push_actions(push_mode)
        }
        
        return result
    
    def _get_push_actions(self, push_mode: str) -> List[str]:
        """获取推送操作选项"""
        mode_info = self.config_manager.get_push_modes().get(push_mode, {})
        return mode_info.get("actions", ["display"])
    
    def push_to_wechat(self, article_id: str) -> Dict:
        """推送文章到微信草稿箱"""
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


# 便捷函数
def query_articles(user_input: str, user_id: str = "insurance_agent", 
                   config: Dict = None) -> Dict:
    """便捷查询函数"""
    engine = QueryEngine()
    return engine.query(user_input, user_id, config)


def recommend_and_push(user_input: str, user_id: str = "insurance_agent",
                       push_mode: str = None) -> Dict:
    """查询并推送"""
    config = {}
    if push_mode:
        config["push_mode"] = push_mode
    
    engine = QueryEngine()
    result = engine.query(user_input, user_id, config)
    
    if result["status"] != "success":
        return result
    
    # 检查推送模式
    actual_push_mode = result.get("push_mode", "confirm")
    
    if actual_push_mode == "auto_draft":
        # 自动推送
        article_id = result["recommendation"]["article_id"]
        push_result = engine.push_to_wechat(article_id)
        result["push_result"] = push_result
    
    return result


if __name__ == '__main__':
    print("🧪 测试可配置查询引擎\n")
    
    # 测试不同策略
    test_configs = [
        {"recall_strategy": "topic_exact", "filter_strategy": "top_n"},
        {"recall_strategy": "hybrid", "filter_strategy": "weighted_random"},
        {"recall_strategy": "quality_first", "filter_strategy": "diversity"}
    ]
    
    for i, cfg in enumerate(test_configs, 1):
        print(f"\n测试配置 {i}: {cfg}")
        result = query_articles("客户经营技巧", config=cfg)
        
        if result["status"] == "success":
            print(f"  ✅ 推荐: {result['recommendation']['title'][:40]}...")
            print(f"  🔧 策略: 召回={cfg['recall_strategy']}, 筛选={cfg['filter_strategy']}")
        else:
            print(f"  ❌ {result['message']}")
