#!/usr/bin/env python3
"""
微信公众号草稿箱状态同步模块
检查草稿箱中的文章是否被删除，如果删除则回退到文章库状态
"""

import requests
import sqlite3
import sys
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')

class WechatDraftSync:
    """微信草稿箱同步器"""
    
    def __init__(self, app_id: str, app_secret: str, db_path: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.db_path = db_path
        self.access_token = None
    
    def _get_access_token(self) -> str:
        """获取微信access_token"""
        url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}'
        try:
            resp = requests.get(url, timeout=30)
            data = resp.json()
            self.access_token = data.get('access_token')
            return self.access_token
        except Exception as e:
            print(f"获取token失败: {e}")
            return None
    
    def _check_draft_exists(self, media_id: str) -> bool:
        """检查特定草稿是否还存在"""
        if not self.access_token:
            self._get_access_token()
        
        url = f"https://api.weixin.qq.com/cgi-bin/draft/get?access_token={self.access_token}"
        data = {"media_id": media_id}
        
        try:
            resp = requests.post(url, json=data, timeout=30)
            result = resp.json()
            # 如果返回了news_item或title，说明草稿存在
            return 'news_item' in result or 'title' in result
        except Exception as e:
            print(f"检查草稿失败: {e}")
            return False
    
    def sync_draft_status(self) -> Dict:
        """
        同步草稿箱状态
        检查所有在草稿箱状态的文章是否还在草稿箱中
        如果不在（被删除），则回退到文章库状态
        
        Returns:
            {
                'checked': 检查数量,
                'exists': 仍然存在的数量,
                'reverted': 回退到文章库的数量,
                'errors': 检查失败的数量,
                'details': 详细信息列表
            }
        """
        print("🔄 开始同步草稿箱状态...")
        
        # 获取所有标记为草稿箱状态的文章
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT article_id, title, draft_media_id, push_status
                FROM articles 
                WHERE push_status = 'draft_box' AND draft_media_id IS NOT NULL
            ''')
            articles = cursor.fetchall()
        
        if not articles:
            print("✓ 没有草稿箱状态的文章需要检查")
            return {'checked': 0, 'exists': 0, 'reverted': 0, 'errors': 0, 'details': []}
        
        print(f"📋 发现 {len(articles)} 篇草稿箱状态的文章需要检查")
        
        results = {
            'checked': 0,
            'exists': 0,
            'reverted': 0,
            'errors': 0,
            'details': []
        }
        
        for article_id, title, media_id, push_status in articles:
            print(f"\n  检查: {title[:30]}...")
            print(f"    Media ID: {media_id[:20]}...")
            
            exists = self._check_draft_exists(media_id)
            results['checked'] += 1
            
            if exists is None:
                results['errors'] += 1
                status_msg = "检查失败"
                detail = {'article_id': article_id, 'title': title, 'action': 'error'}
            elif exists:
                results['exists'] += 1
                status_msg = "✓ 仍在草稿箱"
                detail = {'article_id': article_id, 'title': title, 'action': 'exists'}
            else:
                # 草稿已被删除，回退到文章库状态
                results['reverted'] += 1
                status_msg = "✗ 草稿已删除，回退到文章库"
                
                # 更新数据库，回退到文章库状态
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE articles 
                        SET push_status = 'article_library',
                            draft_push_log = ?,
                            draft_checked_at = ?
                        WHERE article_id = ?
                    ''', (f"草稿被删除，从草稿箱回退到文章库", datetime.now().isoformat(), article_id))
                    conn.commit()
                
                detail = {'article_id': article_id, 'title': title, 'action': 'reverted'}
            
            print(f"    状态: {status_msg}")
            results['details'].append(detail)
        
        print(f"\n✅ 同步完成:")
        print(f"  检查: {results['checked']} 篇")
        print(f"  存在: {results['exists']} 篇")
        print(f"  回退: {results['reverted']} 篇 (草稿被删除)")
        print(f"  失败: {results['errors']} 篇")
        
        return results
    
    def get_draft_status_report(self) -> List[Dict]:
        """获取推送状态报告"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT article_id, title, push_status, draft_media_id, 
                       draft_pushed_at, draft_checked_at
                FROM articles 
                WHERE push_status != 'article_library'
                ORDER BY draft_pushed_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]


# 便捷函数
def sync_draft_status():
    """同步草稿箱状态（便捷函数）"""
    import os
    
    app_id = os.environ.get('WECHAT_APP_ID', 'wx5c6f2e9b5734ddd5')
    app_secret = os.environ.get('WECHAT_APP_SECRET', 'baf071b9ca8e805992a26111c552b9f9')
    db_path = '/root/.openclaw/workspace/content-pipeline/article_library/library.db'
    
    syncer = WechatDraftSync(app_id, app_secret, db_path)
    return syncer.sync_draft_status()


def get_draft_report():
    """获取草稿箱报告（便捷函数）"""
    import os
    
    app_id = os.environ.get('WECHAT_APP_ID', 'wx5c6f2e9b5734ddd5')
    app_secret = os.environ.get('WECHAT_APP_SECRET', 'baf071b9ca8e805992a26111c552b9f9')
    db_path = '/root/.openclaw/workspace/content-pipeline/article_library/library.db'
    
    syncer = WechatDraftSync(app_id, app_secret, db_path)
    return syncer.get_draft_status_report()


if __name__ == '__main__':
    # 测试同步
    print("🚀 测试草稿箱状态同步")
    print("="*60)
    results = sync_draft_status()
    print("\n" + "="*60)
    print("📊 报告:")
    for item in results.get('details', []):
        action = item.get('action', '')
        if action == 'reverted':
            print(f"  ↺ {item['title'][:40]}... (回退到文章库)")
        elif action == 'exists':
            print(f"  ✓ {item['title'][:40]}... (仍在草稿箱)")
        else:
            print(f"  ? {item['title'][:40]}... (检查失败)")
