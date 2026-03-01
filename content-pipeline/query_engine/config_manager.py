"""
查询引擎配置管理
支持策略选择、Prompt配置、推送模式配置
"""

import json
import os
from typing import Dict, List, Any

class QueryConfig:
    """查询引擎配置管理器"""
    
    def __init__(self, config_path: str = None):
        """初始化配置"""
        if config_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, 'config.json')
        
        self.config_path = config_path
        self.config = self._load_config()
        
        # 用户自定义配置（运行时修改）
        self.user_config = {}
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "recall_strategies": {},
            "filter_strategies": {},
            "push_modes": {},
            "default_config": {
                "recall_strategy": "hybrid",
                "filter_strategy": "top_n",
                "push_mode": "confirm",
                "display": {
                    "show_process": True,
                    "show_candidates": True,
                    "show_reason": True,
                    "show_similar": False,
                    "max_alternatives": 2
                }
            }
        }
    
    def get_recall_strategies(self) -> Dict[str, Dict]:
        """获取所有召回策略"""
        return self.config.get("recall_strategies", {})
    
    def get_filter_strategies(self) -> Dict[str, Dict]:
        """获取所有筛选策略"""
        return self.config.get("filter_strategies", {})
    
    def get_push_modes(self) -> Dict[str, Dict]:
        """获取所有推送模式"""
        return self.config.get("push_modes", {})
    
    def get_display_options(self) -> Dict[str, Any]:
        """获取显示选项"""
        return self.config.get("display_options", {})
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return self.config.get("default_config", {})
    
    def set_user_config(self, key: str, value: Any):
        """设置用户配置"""
        self.user_config[key] = value
    
    def get_effective_config(self) -> Dict[str, Any]:
        """获取生效的配置（默认 + 用户自定义）"""
        default = self.get_default_config()
        effective = {
            "recall_strategy": self.user_config.get("recall_strategy", default.get("recall_strategy")),
            "filter_strategy": self.user_config.get("filter_strategy", default.get("filter_strategy")),
            "push_mode": self.user_config.get("push_mode", default.get("push_mode")),
            "display": {**default.get("display", {}), **self.user_config.get("display", {})},
            "source": {**default.get("source", {}), **self.user_config.get("source", {})},
        }
        return effective
    
    def get_strategy_params(self, strategy_type: str, strategy_name: str) -> Dict:
        """获取策略参数"""
        if strategy_type == "recall":
            strategies = self.get_recall_strategies()
        elif strategy_type == "filter":
            strategies = self.get_filter_strategies()
        else:
            return {}
        
        strategy = strategies.get(strategy_name, {})
        return strategy.get("params", {})
    
    def validate_config(self, config: Dict) -> tuple[bool, str]:
        """验证配置是否有效"""
        recall_strategy = config.get("recall_strategy")
        filter_strategy = config.get("filter_strategy")
        push_mode = config.get("push_mode")
        
        if recall_strategy not in self.get_recall_strategies():
            return False, f"无效的召回策略: {recall_strategy}"
        
        if filter_strategy not in self.get_filter_strategies():
            return False, f"无效的筛选策略: {filter_strategy}"
        
        if push_mode not in self.get_push_modes():
            return False, f"无效的推送模式: {push_mode}"
        
        return True, "配置有效"
    
    def get_strategy_info(self, strategy_type: str, strategy_name: str) -> Dict:
        """获取策略详细信息"""
        if strategy_type == "recall":
            strategies = self.get_recall_strategies()
        elif strategy_type == "filter":
            strategies = self.get_filter_strategies()
        elif strategy_type == "push":
            strategies = self.get_push_modes()
        else:
            return {}
        
        return strategies.get(strategy_name, {})
    
    def export_config(self) -> Dict:
        """导出完整配置"""
        return {
            "system_config": self.config,
            "user_config": self.user_config,
            "effective_config": self.get_effective_config()
        }


# 全局配置实例
_query_config = None

def get_config() -> QueryConfig:
    """获取全局配置实例"""
    global _query_config
    if _query_config is None:
        _query_config = QueryConfig()
    return _query_config


if __name__ == '__main__':
    # 测试
    config = get_config()
    print("📋 查询引擎配置")
    print(f"\n召回策略:")
    for key, info in config.get_recall_strategies().items():
        print(f"  - {key}: {info['name']}")
    
    print(f"\n筛选策略:")
    for key, info in config.get_filter_strategies().items():
        print(f"  - {key}: {info['name']}")
    
    print(f"\n推送模式:")
    for key, info in config.get_push_modes().items():
        print(f"  - {key}: {info['name']}")
    
    print(f"\n默认配置:")
    print(json.dumps(config.get_default_config(), ensure_ascii=False, indent=2))
