#!/usr/bin/env python3
"""
用户偏好管理系统
支持多用户、个性化配置、文章库隔离
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class UserPreferenceManager:
    """用户偏好管理器"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            base_path = Path('/root/.openclaw/workspace/content-pipeline')
            db_path = base_path / 'user_preferences.db'
        self.db_path = str(db_path)
        self._init_db()
    
    def _init_db(self):
        """初始化用户数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT,
                    industry TEXT DEFAULT 'general',  -- insurance / tech / finance / etc
                    role TEXT DEFAULT 'agent',  -- agent / manager / content_creator
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP
                )
            ''')
            
            # 用户偏好表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    pref_key TEXT NOT NULL,
                    pref_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, pref_key)
                )
            ''')
            
            # 用户文章库关联表（记录用户生成的文章）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    article_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, article_id)
                )
            ''')
            
            conn.commit()
    
    def create_user(self, user_id: str, name: str, email: str = None, 
                   industry: str = 'general', role: str = 'agent') -> bool:
        """创建新用户"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, name, email, industry, role, last_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, name, email, industry, role, datetime.now().isoformat()))
                conn.commit()
                return True
        except Exception as e:
            print(f"创建用户失败: {e}")
            return False
    
    def set_preference(self, user_id: str, key: str, value: str):
        """设置用户偏好"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_preferences (user_id, pref_key, pref_value, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, key, value, datetime.now().isoformat()))
            conn.commit()
    
    def get_preference(self, user_id: str, key: str, default=None) -> str:
        """获取用户偏好"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pref_value FROM user_preferences 
                WHERE user_id = ? AND pref_key = ?
            ''', (user_id, key))
            row = cursor.fetchone()
            return row[0] if row else default
    
    def get_user_profile(self, user_id: str) -> Dict:
        """获取用户完整画像"""
        profile = {
            'user_id': user_id,
            'name': '',
            'email': '',
            'industry': 'general',
            'role': 'agent',
            'preferences': {}
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 基本信息
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            if user:
                profile.update({
                    'name': user['name'],
                    'email': user['email'],
                    'industry': user['industry'],
                    'role': user['role']
                })
            
            # 偏好设置
            cursor.execute('SELECT pref_key, pref_value FROM user_preferences WHERE user_id = ?', (user_id,))
            for row in cursor.fetchall():
                profile['preferences'][row['pref_key']] = row['pref_value']
        
        return profile
    
    def get_user_generator_config(self, user_id: str) -> Dict:
        """
        获取用户专用的生成器配置
        
        根据用户行业和偏好返回不同的生成策略
        """
        profile = self.get_user_profile(user_id)
        industry = profile.get('industry', 'general')
        
        # 默认配置
        config = {
            'target_audience': '保险代理人' if industry == 'insurance' else '一般读者',
            'avoid_technical': industry == 'insurance',  # 保险行业避免技术术语
            'focus_areas': [],
            'writing_style': 'practical',  # practical / technical / story
            'article_types': []
        }
        
        # 保险行业专用配置
        if industry == 'insurance':
            config.update({
                'target_audience': '保险代理人（保险业务员）',
                'avoid_technical': True,
                'focus_areas': [
                    '保险客户经营（给客户看的）',
                    '保险获客（给代理人看的）'
                ],
                'writing_style': 'practical',  # 实战导向
                'article_types': [
                    '故事案例派',
                    '话术实战派',
                    '情感连接派',
                    '转介绍技巧派',
                    '社群经营派'
                ],
                'forbidden_words': [
                    '数字化', 'SaaS', 'CRM', '私域流量', '数据中台',
                    '算法', 'API', '接口', '部署', '架构'
                ],
                'preferred_words': [
                    '跟进', '回访', '约访', '促成', '缘故客户',
                    '转介绍', '保单', '保障', '理赔', '服务'
                ]
            })
        
        # 科技行业配置
        elif industry == 'tech':
            config.update({
                'target_audience': '科技从业者',
                'avoid_technical': False,
                'focus_areas': [
                    'AI工具应用',
                    '数字化转型',
                    '效率提升'
                ],
                'writing_style': 'technical',
                'article_types': [
                    '深度分析派',
                    '实战教程派',
                    '趋势预测派',
                    '工具测评派'
                ]
            })
        
        return config
    
    def list_users(self) -> List[Dict]:
        """列出所有用户"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def associate_article(self, user_id: str, article_id: str):
        """关联文章到用户"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO user_articles (user_id, article_id)
                VALUES (?, ?)
            ''', (user_id, article_id))
            conn.commit()


# 便捷函数
def get_user_config(user_id: str) -> Dict:
    """获取用户配置（便捷函数）"""
    manager = UserPreferenceManager()
    return manager.get_user_generator_config(user_id)


def create_insurance_user(user_id: str, name: str, email: str = None):
    """创建保险行业用户（便捷函数）"""
    manager = UserPreferenceManager()
    manager.create_user(user_id, name, email, industry='insurance', role='agent')
    
    # 设置保险行业默认偏好
    manager.set_preference(user_id, 'primary_topic', '保险客户经营')
    manager.set_preference(user_id, 'secondary_topic', '保险获客')
    manager.set_preference(user_id, 'content_style', 'practical')
    manager.set_preference(user_id, 'avoid_technical', 'true')
    manager.set_preference(user_id, 'preferred_angle', '话术实战派')
    
    return True


if __name__ == '__main__':
    # 测试
    print("🧪 测试用户偏好管理")
    
    manager = UserPreferenceManager()
    
    # 创建保险用户
    print("\n创建保险用户...")
    create_insurance_user('insurance_agent_001', '张代理人', 'agent@example.com')
    
    # 获取配置
    config = manager.get_user_generator_config('insurance_agent_001')
    print(f"\n保险用户配置:")
    print(f"  目标受众: {config['target_audience']}")
    print(f"  避免技术术语: {config['avoid_technical']}")
    print(f"  重点领域: {config['focus_areas']}")
    print(f"  文章类型: {config['article_types'][:3]}...")
    
    print("\n✅ 测试完成")
