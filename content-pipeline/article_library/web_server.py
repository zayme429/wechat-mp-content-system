#!/usr/bin/env python3
"""
文章管理库 Web 界面 - 完整管理版
支持查询 + 审核 + 删除 + 修改 + 批注
"""

from flask import Flask, render_template_string, abort, jsonify, request, redirect, flash
from pathlib import Path
import sys
import json
import sqlite3

sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')

from article_library.library import ArticleLibrary
from article_library.user_manager import UserPreferenceManager

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 用于 flash 消息

# 添加自定义过滤器
@app.template_filter('fromjson')
def fromjson_filter(value):
    """将JSON字符串解析为Python对象"""
    if not value:
        return None
    try:
        return json.loads(value)
    except:
        return None

library = ArticleLibrary()
user_manager = UserPreferenceManager()

# 默认用户（保险代理人）
DEFAULT_USER_ID = 'insurance_agent'

# 查询页面模板（带管理功能）
QUERY_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文章库管理 | 微信公众号</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        header {
            background: linear-gradient(135deg, #07c160 0%, #059e4c 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
        }
        h1 { font-size: 28px; margin-bottom: 10px; }
        .subtitle { opacity: 0.9; font-size: 14px; }
        
        /* Flash 消息 */
        .flash-messages {
            margin-bottom: 20px;
        }
        .flash {
            padding: 12px 20px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .flash-success { background: #e8f5e9; color: #2e7d32; border: 1px solid #a5d6a7; }
        .flash-error { background: #ffebee; color: #c62828; border: 1px solid #ef9a9a; }
        .flash-info { background: #e3f2fd; color: #1565c0; border: 1px solid #90caf9; }
        
        /* 查询面板 */
        .query-panel {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            margin-bottom: 25px;
        }
        .query-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #333;
        }
        .query-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .query-field {
            display: flex;
            flex-direction: column;
        }
        .query-field label {
            font-size: 13px;
            color: #666;
            margin-bottom: 6px;
        }
        .query-field input,
        .query-field select {
            padding: 10px 12px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.2s;
        }
        .query-field input:focus,
        .query-field select:focus {
            outline: none;
            border-color: #07c160;
        }
        .query-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }
        .btn {
            padding: 10px 24px;
            border-radius: 8px;
            border: none;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary {
            background: #07c160;
            color: white;
        }
        .btn-primary:hover { background: #059e4c; }
        .btn-secondary {
            background: #f0f0f0;
            color: #666;
        }
        .btn-secondary:hover { background: #e0e0e0; }
        .btn-danger {
            background: #ff4d4f;
            color: white;
        }
        .btn-danger:hover { background: #d32f2f; }
        .btn-sm {
            padding: 6px 12px;
            font-size: 12px;
        }
        
        /* 统计栏 */
        .stats-bar {
            background: #f9f9f9;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }
        .stat-item {
            font-size: 14px;
        }
        .stat-value {
            font-weight: bold;
            color: #07c160;
        }
        
        /* 结果列表 */
        .results-panel {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }
        .results-count {
            font-size: 14px;
            color: #666;
        }
        .results-count strong {
            color: #07c160;
            font-size: 18px;
        }
        
        /* 表格样式 */
        .article-table {
            width: 100%;
            border-collapse: collapse;
        }
        .article-table th {
            text-align: left;
            padding: 12px;
            font-size: 13px;
            color: #666;
            font-weight: 500;
            border-bottom: 2px solid #eee;
            white-space: nowrap;
        }
        .article-table td {
            padding: 15px 12px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 14px;
        }
        .article-table tr:hover {
            background: #f9f9f9;
        }
        .col-title {
            max-width: 250px;
        }
        .col-title a {
            color: #333;
            text-decoration: none;
            font-weight: 500;
        }
        .col-title a:hover {
            color: #07c160;
        }
        .col-topic {
            color: #666;
            font-size: 13px;
        }
        .col-score {
            font-weight: bold;
            color: #07c160;
        }
        .col-status {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
        }
        .status-candidate {
            background: #e3f2fd;
            color: #1976d2;
        }
        .status-approved {
            background: #e8f5e9;
            color: #388e3c;
        }
        .status-rejected {
            background: #ffebee;
            color: #d32f2f;
        }
        .status-revision {
            background: #fff3e0;
            color: #f57c00;
        }
        .col-actions {
            white-space: nowrap;
            display: flex;
            gap: 5px;
        }
        
        /* 分页 */
        .pagination {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-top: 25px;
        }
        .page-btn {
            padding: 8px 14px;
            border: 1px solid #e0e0e0;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
            color: #333;
            font-size: 13px;
        }
        .page-btn:hover {
            border-color: #07c160;
            color: #07c160;
        }
        .page-btn.active {
            background: #07c160;
            border-color: #07c160;
            color: white;
        }
        .page-btn.disabled {
            color: #ccc;
            cursor: not-allowed;
        }
        
        /* 空状态 */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        
        /* 模态框 */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 12px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }
        .modal-header {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
        }
        .modal-body {
            margin-bottom: 20px;
        }
        .modal-footer {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            font-size: 13px;
            color: #666;
            margin-bottom: 6px;
        }
        .form-group input,
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
        }
        .form-group textarea {
            resize: vertical;
            min-height: 100px;
        }
        
        @media (max-width: 768px) {
            .query-grid { grid-template-columns: 1fr; }
            .article-table { display: block; overflow-x: auto; }
            .col-actions { flex-wrap: wrap; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 微信公众号文章库管理</h1>
            <p class="subtitle">
                当前用户: <strong>{{ current_user.name }}</strong> | 
                行业: {{ current_user.industry }} |
                <a href="/query" style="color: white; text-decoration: underline;">🔍 智能查询</a> · 
                审核 · 编辑 · 批注 · 删除
            </p>
        </header>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
            <div class="flash-messages">
                {% for category, message in messages %}
                <div class="flash flash-{{ category }}">{{ message }}</div>
                {% endfor %}
            </div>
            {% endif %}
        {% endwith %}
        
        <!-- 用户选择器 -->
        <div class="query-panel" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
            <div class="query-title" style="color: white;">👤 当前用户</div>
            <form method="GET" action="/library" id="userSelectForm">
                <div style="display: flex; gap: 15px; align-items: center;">
                    <select name="user" style="flex: 1; padding: 12px; border-radius: 8px; border: none; font-size: 15px;" onchange="document.getElementById('userSelectForm').submit()">
                        {% for u in all_users %}
                        <option value="{{ u.user_id }}" {% if current_user.user_id == u.user_id %}selected{% endif %}>
                            {{ u.name }} ({{ u.industry }})
                        </option>
                        {% endfor %}
                    </select>
                    <div style="font-size: 14px; opacity: 0.9;">
                        {% if current_user.industry == 'insurance' %}
                        🏢 保险行业 | 注重实战话术
                        {% elif current_user.industry == 'tech' %}
                        💻 科技行业 | 深度分析
                        {% endif %}
                    </div>
                </div>
            </form>
        </div>
        
        <!-- 查询面板 -->
        <div class="query-panel">
            <div class="query-title">🔍 查询条件</div>
            <form method="GET" action="/library">
                <input type="hidden" name="user" value="{{ current_user.user_id }}">
                <div class="query-grid">
                    <div class="query-field">
                        <label>文章ID / 关键词</label>
                        <input type="text" name="q" value="{{ query.q }}" placeholder="输入文章ID或标题关键词">
                    </div>
                    <div class="query-field">
                        <label>主题</label>
                        <select name="topic">
                            <option value="">全部主题</option>
                            {% for t in topics %}
                            <option value="{{ t.topic }}" {% if query.topic == t.topic %}selected{% endif %}>
                                {{ t.topic }} ({{ t.article_count }}篇)
                            </option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="query-field">
                        <label>审核状态</label>
                        <select name="status">
                            <option value="">全部状态</option>
                            <option value="unreviewed" {% if query.status == 'unreviewed' %}selected{% endif %}>⏳ 候选</option>
                            <option value="reviewed_approved" {% if query.status == 'reviewed_approved' %}selected{% endif %}>✓ 审核通过</option>
                            <option value="reviewed_rejected" {% if query.status == 'reviewed_rejected' %}selected{% endif %}>✗ 未通过</option>
                            <option value="reviewed_revision_needed" {% if query.status == 'reviewed_revision_needed' %}selected{% endif %}>📝 需修改</option>
                        </select>
                    </div>
                    <div class="query-field">
                        <label>推送状态</label>
                        <select name="push_status">
                            <option value="">全部</option>
                            <option value="article_library" {% if query.push_status == 'article_library' %}selected{% endif %}>📚 文章库</option>
                            <option value="draft_box" {% if query.push_status == 'draft_box' %}selected{% endif %}>📝 草稿箱</option>
                            <option value="official_published" {% if query.push_status == 'official_published' %}selected{% endif %}>✅ 正式推送</option>
                        </select>
                    </div>
                    <div class="query-field">
                        <label>排序方式</label>
                        <select name="sort">
                            <option value="newest" {% if query.sort == 'newest' %}selected{% endif %}>最新创建</option>
                            <option value="oldest" {% if query.sort == 'oldest' %}selected{% endif %}>最早创建</option>
                            <option value="score_high" {% if query.sort == 'score_high' %}selected{% endif %}>质量分从高</option>
                            <option value="score_low" {% if query.sort == 'score_low' %}selected{% endif %}>质量分从低</option>
                        </select>
                    </div>
                </div>
                <div class="query-actions">
                    <a href="/library?user={{ current_user.user_id }}" class="btn btn-secondary">重置</a>
                    <button type="submit" class="btn btn-primary">🔍 查询</button>
                </div>
                {% if query.q or query.topic or query.status or query.push_status %}
                <div style="margin-top: 10px; font-size: 12px; color: #666;">
                    当前筛选: 
                    {% if query.q %}关键词:{{ query.q }}{% endif %}
                    {% if query.topic %}主题:{{ query.topic }}{% endif %}
                    {% if query.status %}审核:{{ query.status }}{% endif %}
                    {% if query.push_status %}推送:{{ query.push_status }}{% endif %}
                </div>
                {% endif %}
            </form>
        </div>
        
        <!-- 统计栏 -->
        <div class="stats-bar">
            <div class="stat-item">
                文章总数: <span class="stat-value">{{ stats.total }}</span>
            </div>
            <div class="stat-item">
                候选: <span class="stat-value">{{ stats.candidates or 0 }}</span>
            </div>
            <div class="stat-item">
                审核通过: <span class="stat-value">{{ stats.approved or 0 }}</span>
            </div>
            <div class="stat-item">
                需修改: <span class="stat-value">{{ stats.revision or 0 }}</span>
            </div>
        </div>
        
        <!-- 草稿箱同步按钮 -->
        <div style="background: #f0f7ff; border-left: 4px solid #1890ff; padding: 15px 20px; margin-bottom: 20px; border-radius: 0 8px 8px 0; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-size: 14px; font-weight: 500; color: #1890ff; margin-bottom: 4px;">
                    📤 微信公众号草稿箱同步
                </div>
                <div style="font-size: 12px; color: #666;">
                    检查已推送的文章是否还在草稿箱中（若您在公众号后台删除了文章，点击同步可更新状态）
                </div>
            </div>
            <a href="/admin/sync-drafts" class="btn btn-primary" style="background: #1890ff; white-space: nowrap;">🔄 同步草稿箱状态</a>
        </div>
        
        <!-- 草稿箱状态显示 -->
        {% if draft_sync_result %}
        <div style="background: {% if draft_sync_result.reverted > 0 %}#fffbe6{% else %}#f6ffed{% endif %}; border-left: 4px solid {% if draft_sync_result.reverted > 0 %}#faad14{% else %}#52c41a{% endif %}; padding: 15px 20px; margin-bottom: 20px; border-radius: 0 8px 8px 0;">
            <div style="font-size: 14px; font-weight: 500; color: {% if draft_sync_result.reverted > 0 %}#faad14{% else %}#52c41a{% endif %}; margin-bottom: 8px;">
                {% if draft_sync_result.reverted > 0 %}🔄{% else %}✅{% endif %} 同步完成
            </div>
            <div style="font-size: 13px; color: #666; line-height: 1.8;">
                检查了 {{ draft_sync_result.checked }} 篇文章
                {% if draft_sync_result.exists > 0 %}，{{ draft_sync_result.exists }} 篇仍在草稿箱{% endif %}
                {% if draft_sync_result.reverted > 0 %}，<strong style="color: #faad14;">{{ draft_sync_result.reverted }} 篇已回退到文章库</strong>（草稿被删除）{% endif %}
                {% if draft_sync_result.errors > 0 %}，{{ draft_sync_result.errors }} 篇检查失败{% endif %}
            </div>
            {% if draft_sync_result.reverted > 0 %}
            <div style="font-size: 12px; color: #faad14; margin-top: 8px;">
                提示：草稿被删除的文章已自动回退到"文章库"状态
            </div>
            {% endif %}
        </div>
        {% endif %}
        
        <!-- 结果列表 -->
        <div class="results-panel">
            <div class="results-header">
                <div class="results-count">
                    共找到 <strong>{{ total_count }}</strong> 篇文章
                    {% if query.q or query.topic or query.status %}
                    <span style="color: #999; font-weight: normal;">（已应用筛选）</span>
                    {% endif %}
                </div>
            </div>
            
            <!-- 实现路径说明 -->
            <div style="background: #f0f7ff; border-left: 4px solid #0066cc; padding: 15px 20px; margin-bottom: 20px; border-radius: 0 8px 8px 0;">
                <div style="font-size: 13px; color: #666; margin-bottom: 8px;">
                    <strong>📋 文章生成流程：</strong>
                </div>
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px;">
                    <span style="background: white; padding: 4px 10px; border-radius: 4px; color: #0066cc; border: 1px solid #cce5ff;">主题确定</span>
                    <span style="color: #999;">→</span>
                    <span style="background: white; padding: 4px 10px; border-radius: 4px; color: #0066cc; border: 1px solid #cce5ff;">角度选择</span>
                    <span style="color: #999;">→</span>
                    <span style="background: white; padding: 4px 10px; border-radius: 4px; color: #0066cc; border: 1px solid #cce5ff;">文章生成</span>
                    <span style="color: #999;">→</span>
                    <span style="background: white; padding: 4px 10px; border-radius: 4px; color: #0066cc; border: 1px solid #cce5ff;">质量评估</span>
                    <span style="color: #999;">→</span>
                    <span style="background: white; padding: 4px 10px; border-radius: 4px; color: #0066cc; border: 1px solid #cce5ff;">入库待审</span>
                </div>
            </div>
            
            {% if articles %}
            <table class="article-table">
                <thead>
                    <tr>
                        <th>文章ID</th>
                        <th>标题</th>
                        <th>质量分</th>
                        <th>审核状态</th>
                        <th>草稿箱状态</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {% for article in articles %}
                    <tr>
                        <td><code style="background: #f5f5f5; padding: 2px 6px; border-radius: 4px; font-size: 11px;">{{ article.article_id[:16] }}...</code></td>
                        <td class="col-title">
                            <a href="/article/{{ article.share_token }}" title="{{ article.title }}">
                                {{ article.title[:35] }}{% if article.title|length > 35 %}...{% endif %}
                            </a>
                            {% if article.review_notes %}
                            <div style="font-size: 11px; color: #f57c00; margin-top: 4px;">💬 有批注</div>
                            {% endif %}
                        </td>
                        <td class="col-score">{{ "%.1f"|format(article.quality_score) if article.quality_score else '-' }}</td>
                        <td>
                            {% if article.status == 'candidate' %}
                                <span class="col-status status-candidate">候选</span>
                            {% elif article.status == 'reviewed_approved' %}
                                <span class="col-status status-approved">✓ 通过</span>
                            {% elif article.status == 'reviewed_rejected' %}
                                <span class="col-status status-rejected">✗ 拒绝</span>
                            {% elif article.status == 'reviewed_revision_needed' %}
                                <span class="col-status status-revision">需修改</span>
                            {% else %}
                                <span class="col-status">{{ article.status }}</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if article.push_status == 'article_library' %}
                                <span style="color: #666; font-size: 12px;">📚 文章库</span>
                            {% elif article.push_status == 'draft_box' %}
                                <span style="color: #1890ff; font-size: 12px;">📝 草稿箱</span>
                            {% elif article.push_status == 'official_published' %}
                                <span style="color: #52c41a; font-size: 12px;">✅ 正式推送</span>
                            {% else %}
                                <span style="color: #999; font-size: 12px;">-</span>
                            {% endif %}
                        </td>
                        <td class="col-actions">
                            <a href="/article/{{ article.share_token }}" class="btn btn-sm btn-primary">查看</a>
                            <a href="/article/{{ article.share_token }}/traceability" class="btn btn-sm btn-secondary" style="background: #667eea; color: white;">📊 溯源</a>
                            <a href="/admin/edit/{{ article.article_id }}" class="btn btn-sm btn-secondary">编辑</a>
                            <a href="/admin/review/{{ article.article_id }}" class="btn btn-sm btn-secondary">审核</a>
                            <button onclick="if(confirm('确定删除这篇文章？')) window.location.href='/admin/delete/{{ article.article_id }}'" class="btn btn-sm btn-danger">删除</button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            {% if total_pages > 1 %}
            <div class="pagination">
                {% if page > 1 %}
                <a href="?page={{ page-1 }}{% if query.q %}&q={{ query.q }}{% endif %}{% if query.topic %}&topic={{ query.topic }}{% endif %}{% if query.status %}&status={{ query.status }}{% endif %}{% if query.push_status %}&push_status={{ query.push_status }}{% endif %}{% if query.sort %}&sort={{ query.sort }}{% endif %}" class="page-btn">← 上一页</a>
                {% else %}
                <span class="page-btn disabled">← 上一页</span>
                {% endif %}
                
                {% for p in range(1, total_pages + 1) %}
                    {% if p == page %}
                    <span class="page-btn active">{{ p }}</span>
                    {% else %}
                    <a href="?page={{ p }}{% if query.q %}&q={{ query.q }}{% endif %}{% if query.topic %}&topic={{ query.topic }}{% endif %}{% if query.status %}&status={{ query.status }}{% endif %}{% if query.push_status %}&push_status={{ query.push_status }}{% endif %}{% if query.sort %}&sort={{ query.sort }}{% endif %}" class="page-btn">{{ p }}</a>
                    {% endif %}
                {% endfor %}
                
                {% if page < total_pages %}
                <a href="?page={{ page+1 }}{% if query.q %}&q={{ query.q }}{% endif %}{% if query.topic %}&topic={{ query.topic }}{% endif %}{% if query.status %}&status={{ query.status }}{% endif %}{% if query.push_status %}&push_status={{ query.push_status }}{% endif %}{% if query.sort %}&sort={{ query.sort }}{% endif %}" class="page-btn">下一页 →</a>
                {% else %}
                <span class="page-btn disabled">下一页 →</span>
                {% endif %}
            </div>
            {% endif %}
            
            {% else %}
            <div class="empty-state">
                <p>没有找到符合条件的文章</p>
                <p style="font-size: 13px; margin-top: 10px;">尝试调整查询条件或<a href="/library" style="color: #07c160;">重置筛选</a></p>
            </div>
            {% endif %}
        </div>
    </div>
    
    <!-- 审核模态框 -->
    <div id="reviewModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">📝 文章审核</div>
            <div class="modal-body">
                <form id="reviewForm" method="POST" action="/admin/review">
                    <input type="hidden" name="article_id" id="reviewArticleId">
                    <div class="form-group">
                        <label>文章标题</label>
                        <input type="text" id="reviewArticleTitle" readonly style="background: #f5f5f5;">
                    </div>
                    <div class="form-group">
                        <label>审核结果 <span style="color: red;">*</span></label>
                        <select name="result" required>
                            <option value="">请选择</option>
                            <option value="approved">✓ 审核通过</option>
                            <option value="rejected">✗ 不通过</option>
                            <option value="revision_needed">📝 需要修改</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>审核意见 / 修改建议</label>
                        <textarea name="notes" placeholder="输入审核意见或修改建议..."></textarea>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button onclick="closeReviewModal()" class="btn btn-secondary">取消</button>
                <button onclick="submitReview()" class="btn btn-primary">提交审核</button>
            </div>
        </div>
    </div>
    
    <script>
        function openReviewModal(articleId, title) {
            document.getElementById('reviewArticleId').value = articleId;
            document.getElementById('reviewArticleTitle').value = title || '';
            document.getElementById('reviewModal').style.display = 'flex';
        }
        
        function closeReviewModal() {
            document.getElementById('reviewModal').style.display = 'none';
        }
        
        function submitReview() {
            document.getElementById('reviewForm').submit();
        }
        
        function confirmDelete(articleId, title) {
            if (confirm('确定要删除文章 "' + title + '" 吗？\n\n此操作不可恢复！')) {
                window.location.href = '/admin/delete/' + articleId;
            }
        }
        
        // 点击模态框外部关闭
        document.getElementById('reviewModal').addEventListener('click', function(e) {
            if (e.target === this) closeReviewModal();
        });
        
        // 表单提交验证
        document.getElementById('reviewForm').addEventListener('submit', function(e) {
            var result = document.querySelector('select[name="result"]').value;
            if (!result) {
                e.preventDefault();
                alert('请选择审核结果');
                return false;
            }
        });
    </script>
</body>
</html>
'''


# 编辑页面模板
EDIT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>编辑文章 | {{ article.title[:30] }}...</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
        
        header {
            background: linear-gradient(135deg, #07c160 0%, #059e4c 100%);
            color: white;
            padding: 20px 30px;
            border-radius: 12px;
            margin-bottom: 25px;
        }
        h1 { font-size: 22px; }
        
        .edit-panel {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            font-size: 14px;
            color: #333;
            margin-bottom: 8px;
            font-weight: 500;
        }
        .form-group input[type="text"],
        .form-group select {
            width: 100%;
            padding: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
        }
        .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            font-family: 'Consolas', 'Monaco', monospace;
            resize: vertical;
            min-height: 400px;
            line-height: 1.8;
        }
        
        .info-box {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 13px;
            color: #666;
        }
        .info-box code {
            background: #e8e8e8;
            padding: 2px 6px;
            border-radius: 4px;
        }
        
        .btn {
            padding: 12px 30px;
            border-radius: 8px;
            border: none;
            font-size: 14px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary {
            background: #07c160;
            color: white;
        }
        .btn-secondary {
            background: #f0f0f0;
            color: #666;
            margin-right: 10px;
        }
        
        .actions {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>✏️ 编辑文章</h1>
        </header>
        
        <div class="edit-panel">
            <div class="info-box">
                <strong>文章ID:</strong> <code>{{ article.article_id }}</code> &nbsp;|&nbsp;
                <strong>创建时间:</strong> {{ article.created_at }} &nbsp;|&nbsp;
                <strong>当前状态:</strong> {{ article.status }}
            </div>
            
            <form method="POST" action="/admin/edit/{{ article.article_id }}">
                <div class="form-group">
                    <label>文章标题</label>
                    <input type="text" name="title" value="{{ article.title }}" required>
                </div>
                
                <div class="form-group">
                    <label>主题</label>
                    <input type="text" name="topic" value="{{ article.topic }}" required>
                </div>
                
                <div class="form-group">
                    <label>写作角度</label>
                    <input type="text" name="angle" value="{{ article.angle or '' }}">
                </div>
                
                <div class="form-group">
                    <label>文章内容 (支持 Markdown)</label>
                    <textarea name="content" required>{{ article.content }}</textarea>
                </div>
                
                <div class="actions">
                    <a href="/library" class="btn btn-secondary">取消</a>
                    <button type="submit" class="btn btn-primary">💾 保存修改</button>
                </div>
            </form>
        </div>
    </div>
</body>
</html>
'''


@app.route('/library')
def library_view():
    """文章库查询页面"""
    # 获取当前用户（默认保险代理人）
    current_user_id = request.args.get('user', DEFAULT_USER_ID)
    
    # 获取用户信息
    current_user = user_manager.get_user_profile(current_user_id)
    all_users = user_manager.list_users()
    
    query = {
        'q': request.args.get('q', ''),
        'topic': request.args.get('topic', ''),
        'status': request.args.get('status', ''),
        'push_status': request.args.get('push_status', ''),
        'sort': request.args.get('sort', 'newest'),
        'page': int(request.args.get('page', 1)),
        'user': current_user_id
    }
    
    page_size = 20
    
    # 获取当前用户的文章ID列表
    user_article_ids = []
    if current_user_id:
        with sqlite3.connect(user_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT article_id FROM user_articles WHERE user_id = ?', (current_user_id,))
            user_article_ids = [row[0] for row in cursor.fetchall()]
    
    # 构建SQL查询
    where_clauses = ['1=1']
    params = []
    
    # 用户筛选（如果指定了用户且该用户有关联文章）
    if current_user_id and user_article_ids:
        placeholders = ','.join(['?' for _ in user_article_ids])
        where_clauses.append(f'article_id IN ({placeholders})')
        params.extend(user_article_ids)
    
    if query['q']:
        where_clauses.append('(article_id LIKE ? OR title LIKE ?)')
        params.extend([f'%{query["q"]}%', f'%{query["q"]}%'])
    
    if query['topic']:
        where_clauses.append('topic = ?')
        params.append(query['topic'])
    
    if query['status']:
        if query['status'] == 'unreviewed':
            # 未审核：包括 candidate 和 imported 状态
            where_clauses.append("(status = 'candidate' OR status = 'imported')")
        else:
            where_clauses.append('status = ?')
            params.append(query['status'])
    
    if query['push_status']:
        where_clauses.append('push_status = ?')
        params.append(query['push_status'])
    
    sort_map = {
        'newest': 'created_at DESC',
        'oldest': 'created_at ASC',
        'score_high': 'quality_score DESC',
        'score_low': 'quality_score ASC'
    }
    order_by = sort_map.get(query['sort'], 'created_at DESC')
    
    with sqlite3.connect(library.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        count_sql = f"SELECT COUNT(*) FROM articles WHERE {' AND '.join(where_clauses)}"
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]
        
        offset = (query['page'] - 1) * page_size
        sql = f'''
            SELECT * FROM articles 
            WHERE {' AND '.join(where_clauses)}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        '''
        cursor.execute(sql, params + [page_size, offset])
        
        columns = [desc[0] for desc in cursor.description]
        articles = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    total_pages = (total_count + page_size - 1) // page_size
    stats = library.get_library_stats()
    
    # 获取草稿箱同步结果（如果有）
    draft_sync_result = session.pop('draft_sync_result', None)
    
    return render_template_string(QUERY_TEMPLATE,
                                  query=query,
                                  articles=articles,
                                  stats=stats,
                                  topics=stats.get('topics', []),
                                  total_count=total_count,
                                  total_pages=total_pages,
                                  page=query['page'],
                                  current_user=current_user,
                                  all_users=all_users,
                                  draft_sync_result=draft_sync_result)


# 审核页面模板
REVIEW_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文章审核 | {{ article.title[:30] }}...</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        header {
            background: linear-gradient(135deg, #07c160 0%, #059e4c 100%);
            color: white;
            padding: 20px 30px;
            border-radius: 12px;
            margin-bottom: 25px;
        }
        h1 { font-size: 22px; }
        .review-panel {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        .article-info {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 25px;
        }
        .article-info h3 {
            font-size: 16px;
            margin-bottom: 10px;
        }
        .article-info p {
            font-size: 13px;
            color: #666;
            margin: 5px 0;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
        }
        .form-group textarea {
            resize: vertical;
            min-height: 120px;
        }
        .form-group select:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #07c160;
        }
        .required {
            color: #ff4d4f;
        }
        .actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        .btn {
            padding: 12px 30px;
            border-radius: 8px;
            border: none;
            font-size: 14px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary {
            background: #07c160;
            color: white;
        }
        .btn-primary:hover { background: #059e4c; }
        .btn-secondary {
            background: #f0f0f0;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📝 文章审核</h1>
        </header>
        
        <div class="review-panel">
            <div class="article-info">
                <h3>{{ article.title }}</h3>
                <p><strong>文章ID:</strong> {{ article.article_id }}</p>
                <p><strong>主题:</strong> {{ article.topic }}</p>
                <p><strong>当前状态:</strong> 
                    {% if article.status == 'candidate' %}候选
                    {% elif article.status == 'reviewed_approved' %}✓ 审核通过
                    {% elif article.status == 'reviewed_rejected' %}✗ 未通过
                    {% elif article.status == 'reviewed_revision_needed' %}需修改
                    {% else %}{{ article.status }}{% endif %}
                </p>
                {% if article.quality_score %}
                <p><strong>质量分:</strong> {{ "%.1f"|format(article.quality_score) }}</p>
                {% endif %}
            </div>
            
            {% if article.draft_status %}
            <div style="background: #e8f5e9; border-left: 4px solid #07c160; padding: 15px; margin-bottom: 20px; border-radius: 0 8px 8px 0;">
                <strong>📤 草稿箱状态:</strong> 
                {% if article.draft_status == 'success' %}
                    ✅ 已推送 (Media ID: {{ article.draft_media_id[:20] }}...)
                {% elif article.draft_status == 'failed' %}
                    ❌ 推送失败
                {% else %}
                    ⏳ 推送中...
                {% endif %}
                {% if article.draft_pushed_at %}
                <br><small>推送时间: {{ article.draft_pushed_at }}</small>
                {% endif %}
            </div>
            {% endif %}
            
            <form method="POST" action="/admin/review/{{ article.article_id }}">
                <div class="form-group">
                    <label>审核结果 <span class="required">*</span></label>
                    <select name="result" required>
                        <option value="">请选择审核结果</option>
                        <option value="approved">✓ 审核通过</option>
                        <option value="rejected">✗ 不通过</option>
                        <option value="revision_needed">📝 需要修改</option>
                        <option value="unreviewed">↺ 重置为候选</option>
                        <option value="push_to_draft" style="color: #07c160; font-weight: bold;">🚀 审核通过并推送到草稿箱</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>审核意见 / 修改建议</label>
                    <textarea name="notes" placeholder="请输入审核意见或修改建议（可选）..."></textarea>
                </div>
                
                <div class="actions">
                    <a href="/library" class="btn btn-secondary">取消</a>
                    <button type="submit" class="btn btn-primary">提交</button>
                </div>
            </form>
        </div>
    </div>
</body>
</html>
'''


def _shorten_title(title: str) -> str:
    """缩短标题到64字节以内，保持吸引力"""
    import re
    
    # 移除markdown标记
    title = title.replace('**', '').replace('*', '').strip()
    
    if len(title.encode('utf-8')) <= 64:
        return title
    
    # 超长时：提取冒号后的核心内容（通常是重点）
    if '：' in title or ':' in title:
        for sep in ['：', ': ']:
            if sep in title:
                parts = title.split(sep, 1)
                if len(parts) > 1:
                    core = parts[1].strip()
                    # 检查核心内容是否合适
                    if 10 < len(core.encode('utf-8')) <= 64 and not core.startswith('如何'):
                        return core
                    # 核心仍超长，继续处理
                    title = core
                    break
    
    # 移除书名号、括号补充说明
    title = title.replace('《', '').replace('》', '')
    title = re.sub(r'（[^）]+）', '', title)
    title = re.sub(r'\([^)]+\)', '', title)
    title = title.strip()
    
    # 移除修饰性前缀但保留核心
    prefixes = ['关于', '浅谈', '深度解析', '一文读懂', '全面解读', 
                '从0到1', '手把手教你', '保姆级教程', '实战指南']
    for prefix in prefixes:
        if title.startswith(prefix):
            title = title[len(prefix):].strip('：: ')
            break
    
    # 简化专业术语但保持可读性
    replacements = [
        ('人工智能', 'AI'),
        ('客户经营', '客情维护'),
        ('方法论', '方法'),
        ('底层逻辑', '核心逻辑'),
        ('自动化工作流', '自动化'),
    ]
    for old, new in replacements:
        title = title.replace(old, new)
    
    # 最后截断到合适长度
    if len(title.encode('utf-8')) > 64:
        while len(title.encode('utf-8')) > 61:
            title = title[:-1]
        title = title + '...'
    
    return title.strip()


def push_to_wechat_draft(article_id):
    """推送到微信公众号草稿箱 - 使用微信API直接推送"""
    import requests
    import urllib.request
    import traceback
    from datetime import datetime
    from article_library.push_logger import log_push_start, log_push_step, log_push_error, log_push_success
    
    article = library.get_article(article_id)
    if not article:
        return False, "文章不存在"
    
    title = article['title'].replace('**', '').strip()
    log_push_start(article_id, title)
    
    # 更新状态为推送中
    with sqlite3.connect(library.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE articles 
            SET push_status = 'draft_box', draft_push_log = ?
            WHERE article_id = ?
        ''', (f"开始推送到草稿箱... {datetime.now().isoformat()}", article_id))
        conn.commit()
    
    try:
        APP_ID = 'wx5c6f2e9b5734ddd5'
        APP_SECRET = 'baf071b9ca8e805992a26111c552b9f9'
        
        # 获取 access_token
        log_push_step("1_GET_TOKEN", "开始获取access_token")
        token_url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}'
        resp = requests.get(token_url, timeout=30)
        token_data = resp.json()
        access_token = token_data.get('access_token')
        
        if not access_token:
            log_push_error(f"获取token失败: {token_data}")
            raise Exception(f"无法获取 access_token: {token_data.get('errmsg', '未知错误')}")
        
        log_push_step("1_GET_TOKEN", "获取token成功", {"token_prefix": access_token[:20]})
        
        # 上传封面为永久素材
        log_push_step("2_UPLOAD_COVER", "开始上传封面为永久素材")
        import urllib.request
        try:
            # 下载封面图片
            cover_url = "https://picsum.photos/200/200"
            urllib.request.urlretrieve(cover_url, "/tmp/thumb_push.jpg")
            
            # 上传为永久素材
            media_url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=thumb"
            with open("/tmp/thumb_push.jpg", "rb") as f:
                files = {"media": ("thumb.jpg", f, "image/jpeg")}
                resp = requests.post(media_url, files=files, timeout=30)
                media_result = resp.json()
            
            log_push_step("2_UPLOAD_COVER", "封面上传结果", media_result)
            
            if "media_id" not in media_result:
                raise Exception(f"封面上传失败: {media_result}")
            
            thumb_media_id = media_result["media_id"]
            log_push_step("2_UPLOAD_COVER", "封面上传成功", {"thumb_media_id": thumb_media_id[:30]})
        except Exception as e:
            log_push_error(f"封面上传失败: {e}")
            raise Exception(f"封面上传失败: {e}")
        
        # 准备文章内容
        log_push_step("3_PREPARE_CONTENT", "准备文章内容")
        content = article['content']
        
        # 清理标题（移除markdown标记，限制字节数不超过64）
        title_clean = title.replace('**', '').replace('*', '').strip()
        # 微信按字节计算标题长度，中文占3字节
        if len(title_clean.encode('utf-8')) > 64:
            # 智能缩短：提取核心主题词
            title_clean = _shorten_title(title_clean)
        log_push_step("3_PREPARE_CONTENT", "清理后的标题", {
            "title": title_clean, 
            "char_count": len(title_clean),
            "byte_count": len(title_clean.encode('utf-8'))
        })
        
        # 简单处理内容：清理markdown标记，转为HTML
        html_content = content.replace('**', '').replace('## ', '').replace('# ', '')
        html_content = html_content.replace('\n\n', '</p><p>').replace('\n', '<br>')
        html_content = '<p>' + html_content + '</p>'
        
        # 推送到草稿箱
        log_push_step("4_PUSH_DRAFT", "开始推送到草稿箱")
        draft_url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
        payload = {
            "articles": [{
                "title": title_clean,
                "thumb_media_id": thumb_media_id,
                "content": html_content,
                "show_cover_pic": 1,
                "need_open_comment": 1,
                "only_fans_can_comment": 0
            }]
        }
        
        log_push_step("4_PUSH_DRAFT", "请求参数", {"title": title[:50], "content_length": len(html_content)})
        
        # 手动编码 JSON，确保中文不被转义
        import json
        json_payload = json.dumps(payload, ensure_ascii=False)
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        resp = requests.post(draft_url, data=json_payload.encode('utf-8'), headers=headers, timeout=30)
        result = resp.json()
        
        log_push_step("4_PUSH_DRAFT", "API响应", result)
        
        if "media_id" in result:
            media_id = result["media_id"]
            log_push_success(media_id)
            
            with sqlite3.connect(library.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE articles 
                    SET push_status = 'draft_box', 
                        draft_media_id = ?,
                        draft_pushed_at = ?,
                        draft_push_log = ?
                    WHERE article_id = ?
                ''', (media_id, datetime.now().isoformat(), f"推送成功: {title_clean}", article_id))
                conn.commit()
            
            return True, f"推送成功！Media ID: {media_id}"
        else:
            error_msg = f"推送失败: {result.get('errmsg', '未知错误')}"
            log_push_error(error_msg, result)
            raise Exception(error_msg)
            
    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()
        log_push_error(error_msg, tb)
        
        # 异常时回退到文章库状态
        with sqlite3.connect(library.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE articles 
                SET push_status = 'article_library',
                    draft_push_log = ?
                WHERE article_id = ?
            ''', (f"推送失败: {error_msg[:300]}", article_id))
            conn.commit()
        
        return False, f"推送失败: {error_msg}"


@app.route('/admin/review/<article_id>', methods=['GET', 'POST'])
def admin_review_page(article_id):
    """审核页面"""
    article = library.get_article(article_id)
    if not article:
        abort(404)
    
    if request.method == 'POST':
        result = request.form.get('result')
        notes = request.form.get('notes', '')
        
        if not result:
            flash('请选择审核结果', 'error')
            return redirect(f'/admin/review/{article_id}')
        
        # 处理重置为未审核
        if result == 'unreviewed':
            import sqlite3
            with sqlite3.connect(library.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE articles 
                    SET status = 'candidate',
                        review_result = NULL,
                        review_notes = ?,
                        reviewed_at = NULL
                    WHERE article_id = ?
                ''', (notes + ' [重置为未审核]', article_id))
                conn.commit()
            flash('✅ 文章已重置为未审核状态', 'success')
            return redirect('/library')
        
        # 处理推送到草稿箱
        if result == 'push_to_draft':
            # 先标记审核通过
            library.mark_reviewed(article_id, 'approved', notes + ' [已推送到草稿箱]')
            
            # 推送到草稿箱
            success, message = push_to_wechat_draft(article_id)
            
            if success:
                flash(f'✅ 审核通过并已推送到草稿箱！{message}', 'success')
            else:
                flash(f'⚠️ 审核通过，但推送失败: {message}', 'warning')
            
            return redirect('/library')
        
        # 普通审核
        success = library.mark_reviewed(article_id, result, notes)
        
        if success:
            status_map = {
                'approved': '审核通过',
                'rejected': '未通过',
                'revision_needed': '需要修改'
            }
            flash(f'文章已标记为「{status_map.get(result, result)}」', 'success')
            return redirect('/library')
        else:
            flash('审核失败', 'error')
    
    return render_template_string(REVIEW_TEMPLATE, article=article)


@app.route('/admin/sync-drafts')
def admin_sync_drafts():
    """同步草稿箱状态"""
    import os
    sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline/article_library')
    from wechat_draft_sync import sync_draft_status
    
    try:
        results = sync_draft_status()
        
        if results['checked'] == 0:
            flash('没有草稿箱状态的文章需要检查', 'info')
        elif results['errors'] > 0:
            flash(f'同步完成，但 {results["errors"]} 篇文章检查失败', 'warning')
        else:
            msg = f'同步完成！检查了 {results["checked"]} 篇文章'
            if results['exists'] > 0:
                msg += f'，{results["exists"]} 篇仍在草稿箱'
            if results['reverted'] > 0:
                msg += f'，{results["reverted"]} 篇已回退到文章库(草稿被删除)'
            flash(msg, 'success')
        
        # 将结果存储在 session 中以便在列表页显示
        session['draft_sync_result'] = results
        
    except Exception as e:
        flash(f'同步失败: {str(e)}', 'error')
    
    return redirect('/library')


# 添加 session 支持
from flask import session
app.secret_key = 'your-secret-key-change-in-production'


@app.route('/admin/delete/<article_id>')
def admin_delete(article_id):
    """删除文章"""
    import sqlite3
    import os
    
    try:
        # 获取文件路径
        article = library.get_article(article_id)
        if article and article.get('file_path'):
            file_path = article['file_path']
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 删除数据库记录
        with sqlite3.connect(library.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM articles WHERE article_id = ?', (article_id,))
            cursor.execute('DELETE FROM article_vectors WHERE article_id = ?', (article_id,))
            cursor.execute('DELETE FROM review_history WHERE article_id = ?', (article_id,))
            conn.commit()
        
        flash('文章已删除', 'success')
    except Exception as e:
        flash(f'删除失败: {str(e)}', 'error')
    
    return redirect('/library')


@app.route('/admin/edit/<article_id>', methods=['GET', 'POST'])
def admin_edit(article_id):
    """编辑文章"""
    article = library.get_article(article_id)
    
    if not article:
        abort(404)
    
    if request.method == 'POST':
        # 保存修改
        title = request.form.get('title')
        topic = request.form.get('topic')
        angle = request.form.get('angle')
        content = request.form.get('content')
        
        import sqlite3
        try:
            with sqlite3.connect(library.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE articles 
                    SET title = ?, topic = ?, angle = ?, content = ?, word_count = ?
                    WHERE article_id = ?
                ''', (title, topic, angle, content, len(content), article_id))
                conn.commit()
            
            # 更新文件
            if article.get('file_path'):
                from pathlib import Path
                file_path = Path(article['file_path'])
                if file_path.exists():
                    md_content = f"""---
article_id: {article_id}
title: {title}
topic: {topic}
angle: {angle}
status: {article.get('status', 'candidate')}
updated_at: {__import__('datetime').datetime.now().isoformat()}
---

{content}
"""
                    file_path.write_text(md_content, encoding='utf-8')
            
            flash('文章已保存', 'success')
            return redirect('/library')
        except Exception as e:
            flash(f'保存失败: {str(e)}', 'error')
    
    return render_template_string(EDIT_TEMPLATE, article=article)


# 保留原来的文章详情页
ARTICLE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ article.title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.8;
        }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #07c160;
            text-decoration: none;
        }
        .article-container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }
        .article-header {
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #f0f0f0;
        }
        .article-title { font-size: 28px; font-weight: 700; color: #222; margin-bottom: 15px; }
        .article-meta { display: flex; flex-wrap: wrap; gap: 15px; font-size: 14px; color: #666; }
        .meta-tag { padding: 4px 12px; border-radius: 4px; font-size: 12px; }
        .tag-candidate { background: #e3f2fd; color: #1976d2; }
        .tag-approved { background: #e8f5e9; color: #388e3c; }
        .tag-rejected { background: #ffebee; color: #d32f2f; }
        .tag-revision { background: #fff3e0; color: #f57c00; }
        .article-content { font-size: 16px; line-height: 1.8; }
        .article-content h1, .article-content h2, .article-content h3 { margin: 30px 0 15px; }
        .article-content p { margin-bottom: 16px; }
        .article-content ul, .article-content ol { margin-bottom: 16px; padding-left: 24px; }
        .article-content blockquote {
            border-left: 4px solid #07c160;
            padding-left: 16px;
            margin: 20px 0;
            color: #555;
            font-style: italic;
        }
        .article-id {
            background: #f5f5f5;
            padding: 10px 15px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 13px;
            margin-bottom: 20px;
            color: #666;
        }
        .review-notes {
            margin-top: 40px;
            padding: 20px;
            background: #fff3e0;
            border-radius: 8px;
            border-left: 4px solid #f57c00;
        }
        .review-notes-title {
            font-weight: 600;
            color: #e65100;
            margin-bottom: 10px;
        }
        .traceability-box {
            margin: 30px 0;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .traceability-title {
            font-size: 14px;
            font-weight: 600;
            color: #667eea;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .traceability-item {
            display: flex;
            margin-bottom: 12px;
            font-size: 13px;
        }
        .traceability-label {
            width: 100px;
            color: #666;
            flex-shrink: 0;
        }
        .traceability-value {
            color: #333;
            flex: 1;
        }
        .path-flow {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .path-step {
            background: white;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            color: #667eea;
            border: 1px solid #e0e0e0;
        }
        .path-arrow {
            color: #999;
            font-size: 12px;
        }
        .actions-bar {
            display: flex;
            gap: 10px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        .btn {
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 14px;
            display: inline-block;
        }
        .btn-primary { background: #07c160; color: white; }
        .btn-secondary { background: #f0f0f0; color: #666; }
        .btn-danger { background: #ff4d4f; color: white; }
        @media (max-width: 768px) {
            .container { padding: 15px; }
            .article-container { padding: 25px; }
            .article-title { font-size: 22px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/library" class="back-link">← 返回文章库</a>
        
        <div class="article-container">
            <div class="article-id">
                📋 文章ID: {{ article.article_id }}
            </div>
            
            <header class="article-header">
                <h1 class="article-title">{{ article.title }}</h1>
                <div class="article-meta">
                    <span>📁 {{ article.topic }}</span>
                    <span>📅 {{ article.created_at[:16] }}</span>
                    {% if article.quality_score %}
                    <span>⭐ {{ "%.1f"|format(article.quality_score) }}</span>
                    {% endif %}
                    {% if article.status == 'candidate' %}
                        <span class="meta-tag tag-candidate">候选</span>
                    {% elif article.status == 'reviewed_approved' %}
                        <span class="meta-tag tag-approved">✓ 审核通过</span>
                    {% elif article.status == 'reviewed_rejected' %}
                        <span class="meta-tag tag-rejected">✗ 未通过</span>
                    {% elif article.status == 'reviewed_revision_needed' %}
                        <span class="meta-tag tag-revision">需要修改</span>
                    {% endif %}
                </div>
                {% if article.angle %}
                <div style="margin-top: 15px; color: #555; font-size: 14px;">
                    🎯 {{ article.angle }}
                </div>
                {% endif %}
            </header>
            
            <!-- 溯源信息 -->
            <div class="traceability-box">
                <div class="traceability-title">
                    📊 文章溯源信息
                </div>
                
                {% if article.generation_path %}
                <div class="traceability-item">
                    <div class="traceability-label">实现路径:</div>
                    <div class="traceability-value">
                        <div class="path-flow">
                            {% for step in article.generation_path.split(' → ') %}
                            <span class="path-step">{{ step }}</span>
                            {% if not loop.last %}<span class="path-arrow">→</span>{% endif %}
                            {% endfor %}
                        </div>
                    </div>
                </div>
                {% endif %}
                
                {% if article.source_info %}
                <div class="traceability-item">
                    <div class="traceability-label">来源信息:</div>
                    <div class="traceability-value">{{ article.source_info }}</div>
                </div>
                {% endif %}
                
                {% if article.angle_type %}
                <div class="traceability-item">
                    <div class="traceability-label">写作角度:</div>
                    <div class="traceability-value">{{ article.angle_type }}</div>
                </div>
                {% endif %}
                
                <div class="traceability-item">
                    <div class="traceability-label">质量评分:</div>
                    <div class="traceability-value">
                        {% if article.quality_score %}
                        <span style="color: #07c160; font-weight: bold;">{{ "%.1f"|format(article.quality_score) }}/10</span>
                        {% else %}-{% endif %}
                    </div>
                </div>
                
                <div class="traceability-item">
                    <div class="traceability-label">候选编号:</div>
                    <div class="traceability-value">候选 {{ article.candidate_num or 1 }}</div>
                </div>
                
                <div class="traceability-item">
                    <div class="traceability-label">生成时间:</div>
                    <div class="traceability-value">{{ article.created_at[:19] }}</div>
                </div>
            </div>
            
            <div class="article-content">
                {{ content_html|safe }}
            </div>
            
            {% if article.review_notes %}
            <div class="review-notes">
                <div class="review-notes-title">💬 审核意见 / 修改建议</div>
                <div>{{ article.review_notes }}</div>
            </div>
            {% endif %}
            
            <div class="actions-bar">
                <a href="/article/{{ article.share_token }}/traceability" class="btn btn-primary">📊 溯源详情</a>
                <a href="/admin/edit/{{ article.article_id }}" class="btn btn-secondary">✏️ 编辑</a>
                <a href="/admin/review/{{ article.article_id }}" class="btn btn-secondary" style="background: #ff9800; color: white;">📝 审核</a>
                <button onclick="if(confirm('确定删除这篇文章？')) window.location.href='/admin/delete/{{ article.article_id }}'" class="btn btn-danger">🗑️ 删除</button>
            </div>
        </div>
    </div>
</body>
</html>
'''


# 溯源详情页面模板
TRACEABILITY_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文章溯源详情 | {{ article.title[:30] }}...</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #07c160;
            text-decoration: none;
        }
        .trace-container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }
        .trace-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .trace-header h1 {
            font-size: 24px;
            margin-bottom: 10px;
        }
        .trace-header p {
            opacity: 0.9;
            font-size: 14px;
        }
        
        /* 区块样式 */
        .section {
            margin-bottom: 30px;
            padding: 20px;
            background: #fafafa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .section-title {
            font-size: 16px;
            font-weight: 600;
            color: #667eea;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .section-content {
            font-size: 14px;
            color: #555;
        }
        
        /* 信息项 */
        .info-item {
            display: flex;
            margin-bottom: 12px;
            padding: 10px 0;
            border-bottom: 1px dashed #e0e0e0;
        }
        .info-item:last-child {
            border-bottom: none;
        }
        .info-label {
            width: 120px;
            color: #666;
            font-weight: 500;
            flex-shrink: 0;
        }
        .info-value {
            flex: 1;
            color: #333;
        }
        
        /* 路径流程 */
        .path-flow {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
            padding: 15px;
            background: white;
            border-radius: 8px;
        }
        .path-step {
            background: #f0f4ff;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            color: #667eea;
            border: 1px solid #d0d8ff;
        }
        .path-arrow {
            color: #999;
        }
        
        /* 文献列表 */
        .literature-list {
            list-style: none;
            padding: 0;
        }
        .literature-item {
            padding: 12px 15px;
            margin-bottom: 10px;
            background: white;
            border-radius: 6px;
            border: 1px solid #e8e8e8;
        }
        .literature-title {
            font-weight: 500;
            color: #0066cc;
            margin-bottom: 5px;
        }
        .literature-source {
            font-size: 12px;
            color: #888;
        }
        .literature-summary {
            font-size: 13px;
            color: #666;
            margin-top: 5px;
        }
        
        /* 关键词标签 */
        .keyword-tag {
            display: inline-block;
            background: #e3f2fd;
            color: #1976d2;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            margin-right: 8px;
            margin-bottom: 5px;
        }
        
        /* JSON代码块 */
        .json-block {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }
        
        .btn {
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 14px;
            display: inline-block;
            margin-top: 20px;
        }
        .btn-primary {
            background: #07c160;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/article/{{ article.share_token }}" class="back-link">← 返回文章</a>
        
        <div class="trace-container">
            <div class="trace-header">
                <h1>📊 文章溯源详情</h1>
                <p>查看文章的完整生成路径、来源信息和参考文献</p>
            </div>
            
            <!-- 文章基本信息 -->
            <div class="section">
                <div class="section-title">📝 文章基本信息</div>
                <div class="section-content">
                    <div class="info-item">
                        <div class="info-label">文章ID:</div>
                        <div class="info-value">{{ article.article_id }}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">标题:</div>
                        <div class="info-value">{{ article.title }}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">主题:</div>
                        <div class="info-value">{{ article.topic }}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">创建时间:</div>
                        <div class="info-value">{{ article.created_at }}</div>
                    </div>
                </div>
            </div>
            
            <!-- 生成路径 -->
            <div class="section">
                <div class="section-title">🔄 实现路径</div>
                <div class="section-content">
                    <div class="path-flow">
                        {% if article.generation_path %}
                            {% for step in article.generation_path.split(' → ') %}
                            <span class="path-step">{{ step }}</span>
                            {% if not loop.last %}<span class="path-arrow">→</span>{% endif %}
                            {% endfor %}
                        {% else %}
                            <span class="path-step">主题确定</span>
                            <span class="path-arrow">→</span>
                            <span class="path-step">角度选择</span>
                            <span class="path-arrow">→</span>
                            <span class="path-step">文章生成</span>
                            <span class="path-arrow">→</span>
                            <span class="path-step">质量评估</span>
                        {% endif %}
                    </div>
                </div>
            </div>
            
            <!-- 主题信息 -->
            {% if article.topic_info %}
            <div class="section">
                <div class="section-title">🎯 主题信息</div>
                <div class="section-content">
                    {% set topic_data = article.topic_info | fromjson %}
                    {% if topic_data %}
                    <div class="info-item">
                        <div class="info-label">确定方式:</div>
                        <div class="info-value">{{ topic_data.get('mode', '自动') }}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">写作方向:</div>
                        <div class="info-value">{{ topic_data.get('direction', '-') }}</div>
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endif %}
            
            <!-- 搜索关键词 -->
            {% if article.search_keywords %}
            <div class="section">
                <div class="section-title">🔍 搜索关键词</div>
                <div class="section-content">
                    {% for keyword in article.search_keywords.split(',') %}
                    <span class="keyword-tag">{{ keyword.strip() }}</span>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
            
            <!-- 参考文献 -->
            {% if article.literature_refs %}
            <div class="section">
                <div class="section-title">📚 参考文献 ({{ article.literature_refs | fromjson | length }}篇)</div>
                <div class="section-content">
                    <ul class="literature-list">
                        {% set refs = article.literature_refs | fromjson %}
                        {% for ref in refs %}
                        <li class="literature-item">
                            <div class="literature-title">[{{ loop.index }}] {{ ref.get('title', '未知标题') }}</div>
                            <div class="literature-source">来源: {{ ref.get('source', '-') }}</div>
                            {% if ref.get('summary') %}
                            <div class="literature-summary">{{ ref.get('summary')[:100] }}{% if ref.get('summary')|length > 100 %}...{% endif %}</div>
                            {% endif %}
                        </li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
            {% endif %}
            
            <!-- 选题理由 -->
            {% if article.angle_reason %}
            <div class="section">
                <div class="section-title">💡 选题理由</div>
                <div class="section-content">
                    <p>{{ article.angle_reason }}</p>
                </div>
            </div>
            {% endif %}
            
            <!-- 来源信息 -->
            <div class="section">
                <div class="section-title">📌 来源信息</div>
                <div class="section-content">
                    <div class="info-item">
                        <div class="info-label">来源:</div>
                        <div class="info-value">{{ article.source_info or 'AI生成' }}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">角度类型:</div>
                        <div class="info-value">{{ article.angle_type or '-' }}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">质量评分:</div>
                        <div class="info-value">{{ "%.1f"|format(article.quality_score) if article.quality_score else '-' }}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">候选编号:</div>
                        <div class="info-value">候选 {{ article.candidate_num or 1 }}</div>
                    </div>
                </div>
            </div>
            
            <!-- 生成参数（调试用） -->
            {% if article.generation_params %}
            <div class="section">
                <div class="section-title">⚙️ 生成参数</div>
                <div class="section-content">
                    <div class="json-block">{{ article.generation_params }}</div>
                </div>
            </div>
            {% endif %}
            
            <a href="/article/{{ article.share_token }}" class="btn btn-primary">← 返回文章详情</a>
        </div>
    </div>
</body>
</html>
'''


@app.route('/article/<share_token>/traceability')
def article_traceability(share_token):
    """文章溯源详情页"""
    article = library.get_article_by_token(share_token)
    if not article:
        abort(404)
    
    return render_template_string(TRACEABILITY_TEMPLATE, article=article)


@app.route('/article/<share_token>')
def article_view(share_token):
    """文章详情页"""
    article = library.get_article_by_token(share_token)
    if not article:
        abort(404)
    
    import re
    content = article.get('content', '')
    
    content_html = content
    content_html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', content_html, flags=re.MULTILINE)
    content_html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content_html, flags=re.MULTILINE)
    content_html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content_html, flags=re.MULTILINE)
    content_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content_html)
    content_html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content_html)
    content_html = re.sub(r'^- (.+)$', r'<li>\1</li>', content_html, flags=re.MULTILINE)
    content_html = re.sub(r'(<li>.+</li>\n)+', r'<ul>\g<0></ul>', content_html)
    content_html = re.sub(r'^(?!<[hlu])(.+)$', r'<p>\1</p>', content_html, flags=re.MULTILINE)
    content_html = re.sub(r'\n+', '', content_html)
    
    return render_template_string(ARTICLE_TEMPLATE, article=article, content_html=content_html)


@app.route('/')
def index():
    return redirect('/library')


# ==================== 查询推荐引擎 ====================

QUERY_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智能文章查询 | 微信公众号</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #07c160 0%, #05a050 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .header h1 { font-size: 24px; margin-bottom: 8px; }
        .header p { opacity: 0.9; font-size: 14px; }
        .query-box {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .query-input {
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .query-input:focus {
            outline: none;
            border-color: #07c160;
        }
        .query-btn {
            width: 100%;
            padding: 15px;
            background: #07c160;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
        }
        .query-btn:hover { background: #06ad56; }
        .result-box {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .process-flow {
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .flow-step {
            text-align: center;
            flex: 1;
        }
        .flow-number {
            width: 40px;
            height: 40px;
            background: #07c160;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 10px;
            font-weight: bold;
        }
        .flow-label { font-size: 12px; color: #666; }
        .flow-value { font-size: 14px; font-weight: 600; color: #333; margin-top: 5px; }
        .recommendation {
            border: 2px solid #07c160;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .rec-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
        }
        .rec-meta {
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
            font-size: 13px;
            color: #666;
        }
        .rec-score {
            background: #07c160;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
        }
        .rec-preview {
            color: #555;
            line-height: 1.6;
            margin-bottom: 15px;
        }
        .push-btn {
            display: inline-block;
            padding: 12px 30px;
            background: #07c160;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 14px;
        }
        .alternatives {
            margin-top: 20px;
        }
        .alt-title {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }
        .alt-item {
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .back-link {
            display: inline-block;
            margin-top: 20px;
            color: #07c160;
            text-decoration: none;
        }
        .no-result {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .no-result-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 智能文章查询</h1>
            <p>输入您的内容需求，系统从文章库智能匹配最合适的文章</p>
        </div>
        
        <div class="query-box">
            <form method="POST" action="/query">
                <input type="text" name="query" class="query-input" 
                       placeholder="例如：客户经营技巧、如何获得转介绍、社群营销方法..."
                       value="{{ query }}" required>
                
                <!-- 策略选择（可折叠） -->
                <div class="strategy-section" style="margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <div style="font-size: 14px; color: #666; margin-bottom: 10px; display: flex; justify-content: space-between;">
                        <span>⚙️ 查询策略配置</span>
                        <a href="/query/config" style="color: #07c160; font-size: 12px;">高级配置 →</a>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <select name="recall_strategy" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">
                            <option value="">默认召回策略</option>
                            <option value="topic_exact">主题精确匹配</option>
                            <option value="keyword_fuzzy">关键词模糊</option>
                            <option value="semantic_vector">语义向量</option>
                            <option value="hybrid">混合策略</option>
                            <option value="quality_first">质量优先</option>
                        </select>
                        <select name="filter_strategy" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">
                            <option value="">默认筛选策略</option>
                            <option value="top_n">Top3随机</option>
                            <option value="threshold">阈值过滤</option>
                            <option value="weighted_random">加权随机</option>
                            <option value="diversity">多样性保证</option>
                        </select>
                    </div>
                    <div style="margin-top: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <select name="source_status" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">
                            <option value="">默认文章状态(仅已审)</option>
                            <option value="reviewed_approved">仅已审(reviewed_approved)</option>
                            <option value="all">全部状态(已审+候选+导入)</option>
                        </select>
                        <select name="source_push_status" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">
                            <option value="">默认推送状态(不限)</option>
                            <option value="article_library">仅文章库(article_library)</option>
                            <option value="all">全部(article_library+draft_box)</option>
                        </select>
                    </div>
                    <div style="margin-top: 10px;">
                        <select name="push_mode" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; width: 100%;">
                            <option value="">默认推送模式</option>
                            <option value="display_only">仅显示推荐</option>
                            <option value="confirm">确认后推送</option>
                            <option value="auto_draft">自动推送（谨慎）</option>
                        </select>
                    </div>
                </div>
                
                <button type="submit" class="query-btn">🔍 智能查询</button>
            </form>
        </div>
        
        {% if result %}
        <div class="result-box">
            {% if result.status == 'success' %}
                <div class="process-flow">
                    <div class="flow-step">
                        <div class="flow-number">1</div>
                        <div class="flow-label">文章池(已审)</div>
                        <div class="flow-value">{{ result.query_process.library_total }}篇</div>
                    </div>
                    <div class="flow-step">
                        <div class="flow-number">2</div>
                        <div class="flow-label">意图识别</div>
                        <div class="flow-value">{{ result.intent.topic }}</div>
                    </div>
                    <div class="flow-step">
                        <div class="flow-number">3</div>
                        <div class="flow-label">召回候选</div>
                        <div class="flow-value">{{ result.query_process.recall_count }}篇</div>
                    </div>
                    <div class="flow-step">
                        <div class="flow-number">4</div>
                        <div class="flow-label">过滤Top</div>
                        <div class="flow-value">{{ result.query_process.filter_top }}篇</div>
                    </div>
                    <div class="flow-step">
                        <div class="flow-number">5</div>
                        <div class="flow-label">随机选择</div>
                        <div class="flow-value">1篇</div>
                    </div>
                </div>
                
                <div class="recommendation">
                    <div class="rec-title">📄 {{ result.recommendation.title }}</div>
                    <div class="rec-meta">
                        <span class="rec-score">匹配分(0-10): {{ "%.1f"|format(result.recommendation.match_score) }}</span>
                        <span>主题: {{ result.recommendation.topic }}</span>
                        <span>角度: {{ result.recommendation.angle_type }}</span>
                    </div>
                    {% if result.recommendation.score_note %}
                    <div style="margin-top: 6px; color: #999; font-size: 12px;">{{ result.recommendation.score_note }}</div>
                    {% endif %}
                    <div class="rec-preview">{{ result.recommendation.content_preview }}</div>
                    
                    {% if result.push_mode == 'auto_draft' %}
                        {% if result.auto_push_result and result.auto_push_result.success %}
                            <div style="background: #e8f5e9; padding: 12px; border-radius: 6px; margin-bottom: 15px;">
                                ✅ 已自动推送到微信草稿箱<br>
                                <small>Media ID: {{ result.auto_push_result.message }}</small>
                            </div>
                        {% else %}
                            <div style="background: #ffebee; padding: 12px; border-radius: 6px; margin-bottom: 15px;">
                                ❌ 自动推送失败: {{ result.auto_push_result.message if result.auto_push_result else '未知错误' }}
                            </div>
                        {% endif %}
                        <a href="/admin/review/{{ result.recommendation.article_id }}" class="push-btn" style="background: #666;">
                            📋 查看文章详情
                        </a>
                    {% else %}
                        <a href="/admin/review/{{ result.recommendation.article_id }}" class="push-btn">
                            🚀 查看详情并推送
                        </a>
                    {% endif %}
                </div>
                
                {% if result.alternatives %}
                <div class="alternatives">
                    <div class="alt-title">📑 其他候选文章（Top {{ result.alternatives|length }}）</div>
                    {% for alt in result.alternatives %}
                    <div class="alt-item">
                        <span>{{ alt.title }}</span>
                        <span style="color: #07c160;">{{ "%.1f"|format(alt.match_score) }}分</span>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            {% else %}
                <div class="no-result">
                    <div class="no-result-icon">😕</div>
                    <h3>没有找到匹配的文章</h3>
                    <p>{{ result.message }}</p>
                    <p style="margin-top: 15px; font-size: 14px;">
                        建议：去<a href="/library" style="color: #07c160;">文章库</a>查看现有文章，或生成新文章
                    </p>
                </div>
            {% endif %}
        </div>
        {% endif %}
        
        <a href="/library" class="back-link">← 返回文章库</a>
    </div>
</body>
</html>
'''

@app.route('/query', methods=['GET', 'POST'])
def query_page():
    """智能查询页面"""
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')
    from query_engine import QueryEngine
    from query_engine.config_manager import get_config
    
    query = ''
    result = None
    custom_config = {}
    
    if request.method == 'POST':
        query = request.form.get('query', '')
        
        # 获取自定义配置
        recall_strategy = request.form.get('recall_strategy')
        filter_strategy = request.form.get('filter_strategy')
        push_mode = request.form.get('push_mode')
        source_status = request.form.get('source_status')
        source_push_status = request.form.get('source_push_status')

        if recall_strategy:
            custom_config['recall_strategy'] = recall_strategy
        if filter_strategy:
            custom_config['filter_strategy'] = filter_strategy
        if push_mode:
            custom_config['push_mode'] = push_mode

        # 召回来源过滤（状态/推送状态）
        source_cfg = {}
        if source_status == 'all':
            source_cfg['statuses'] = ['reviewed_approved', 'candidate', 'imported']
        elif source_status == 'reviewed_approved':
            source_cfg['statuses'] = ['reviewed_approved']

        if source_push_status == 'all':
            source_cfg['push_statuses'] = ['article_library', 'draft_box']
        elif source_push_status == 'article_library':
            source_cfg['push_statuses'] = ['article_library']

        if source_cfg:
            custom_config['source'] = source_cfg
        
        if query:
            engine = QueryEngine()
            result = engine.query(query, custom_config=custom_config if custom_config else None)
            
            # 处理自动推送模式
            if result.get('push_mode') == 'auto_draft' and result.get('status') == 'success':
                article_id = result['recommendation']['article_id']
                push_result = engine.push_to_wechat(article_id)
                result['auto_push_result'] = push_result
    
    return render_template_string(QUERY_PAGE_TEMPLATE, query=query, result=result, custom_config=custom_config)


@app.route('/api/query', methods=['POST'])
def api_query():
    """查询API接口"""
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')
    from query_engine import QueryEngine
    
    data = request.get_json()
    query = data.get('query', '')
    user_id = data.get('user_id', DEFAULT_USER_ID)
    
    if not query:
        return jsonify({"error": "查询内容不能为空"}), 400
    
    engine = QueryEngine()
    result = engine.query(query, user_id)
    
    return jsonify(result)


# ==================== 查询引擎配置管理 ====================

@app.route('/query/prompts', methods=['GET', 'POST'])
def query_prompts_page():
    """Prompt配置页面"""
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')
    from query_engine.prompt_manager import get_prompt_manager
    
    pm = get_prompt_manager()
    
    if request.method == 'POST':
        action = request.form.get('action')
        prompt_key = request.form.get('prompt_key')
        
        if action == 'update':
            template = request.form.get('template')
            name = request.form.get('name')
            description = request.form.get('description')
            
            success = pm.update_prompt(prompt_key, template, name, description)
            if success:
                flash('✅ Prompt已更新', 'success')
            else:
                flash('❌ 更新失败', 'error')
        
        elif action == 'reset':
            success = pm.reset_prompt(prompt_key)
            if success:
                flash('✅ 已恢复默认Prompt', 'success')
            else:
                flash('❌ 恢复失败', 'error')
        
        return redirect('/query/prompts')
    
    prompts = pm.get_all_prompts()
    return render_template_string(PROMPT_TEMPLATE, prompts=prompts)


PROMPT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prompt配置 | 微信公众号</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #07c160 0%, #05a050 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .header h1 { font-size: 24px; margin-bottom: 8px; }
        .header p { opacity: 0.9; font-size: 14px; }
        .prompt-list { display: flex; flex-direction: column; gap: 20px; }
        .prompt-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .prompt-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
        }
        .prompt-title { font-size: 18px; font-weight: 600; color: #333; }
        .prompt-desc { font-size: 13px; color: #666; margin-top: 5px; }
        .prompt-variables {
            font-size: 12px;
            color: #07c160;
            margin-top: 10px;
        }
        .prompt-variables span {
            background: #e8f5e9;
            padding: 2px 8px;
            border-radius: 4px;
            margin-right: 5px;
        }
        .prompt-template {
            width: 100%;
            min-height: 200px;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-family: monospace;
            font-size: 13px;
            resize: vertical;
            margin-top: 15px;
        }
        .prompt-template:focus {
            outline: none;
            border-color: #07c160;
        }
        .prompt-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn-primary { background: #07c160; color: white; }
        .btn-secondary { background: #f0f0f0; color: #666; }
        .back-link {
            display: inline-block;
            margin-top: 20px;
            color: #07c160;
            text-decoration: none;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 20px;
            background: white;
            border-radius: 6px;
            text-decoration: none;
            color: #666;
        }
        .tab.active {
            background: #07c160;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📝 Prompt配置</h1>
            <p>自定义AI提示词模板，控制查询引擎的行为</p>
        </div>
        
        <div class="tabs">
            <a href="/query/config" class="tab">策略配置</a>
            <a href="/query/prompts" class="tab active">Prompt配置</a>
        </div>
        
        <div class="prompt-list">
            {% for key, info in prompts.items() %}
            <div class="prompt-card">
                <form method="POST">
                    <input type="hidden" name="prompt_key" value="{{ key }}">
                    <input type="hidden" name="name" value="{{ info.name }}">
                    <input type="hidden" name="description" value="{{ info.description }}">
                    
                    <div class="prompt-header">
                        <div>
                            <div class="prompt-title">{{ info.name }}</div>
                            <div class="prompt-desc">{{ info.description }}</div>
                            <div class="prompt-variables">
                                变量: {% for var in info.variables %}<span>{{ var }}</span>{% endfor %}
                            </div>
                        </div>
                    </div>
                    
                    <textarea name="template" class="prompt-template">{{ info.template }}</textarea>
                    
                    <div class="prompt-actions">
                        <button type="submit" name="action" value="update" class="btn btn-primary">💾 保存修改</button>
                        <button type="submit" name="action" value="reset" class="btn btn-secondary" 
                                onclick="return confirm('确定恢复默认Prompt？自定义内容将丢失。')">↩️ 恢复默认</button>
                    </div>
                </form>
            </div>
            {% endfor %}
        </div>
        
        <a href="/query" class="back-link">← 返回查询页面</a>
    </div>
</body>
</html>
'''


@app.route('/query/config', methods=['GET', 'POST'])
def query_config_page():
    """查询引擎配置页面"""
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/content-pipeline')
    from query_engine.config_manager import get_config
    
    config_manager = get_config()
    
    if request.method == 'POST':
        # 保存用户配置
        config_manager.set_user_config("recall_strategy", request.form.get('recall_strategy'))
        config_manager.set_user_config("filter_strategy", request.form.get('filter_strategy'))
        config_manager.set_user_config("push_mode", request.form.get('push_mode'))
        config_manager.set_user_config("display", {
            "show_process": request.form.get('show_process') == 'on',
            "show_candidates": request.form.get('show_candidates') == 'on',
            "show_reason": request.form.get('show_reason') == 'on',
            "show_similar": request.form.get('show_similar') == 'on',
            "max_alternatives": int(request.form.get('max_alternatives', 2))
        })
        flash('✅ 配置已保存', 'success')
        return redirect('/query/config')
    
    # 获取所有可用选项
    recall_strategies = config_manager.get_recall_strategies()
    filter_strategies = config_manager.get_filter_strategies()
    push_modes = config_manager.get_push_modes()
    display_options = config_manager.get_display_options()
    current_config = config_manager.get_effective_config()
    
    return render_template_string(CONFIG_TEMPLATE,
                                 recall_strategies=recall_strategies,
                                 filter_strategies=filter_strategies,
                                 push_modes=push_modes,
                                 display_options=display_options,
                                 current_config=current_config)


CONFIG_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>查询引擎配置 | 微信公众号</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #07c160 0%, #05a050 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .header h1 { font-size: 24px; margin-bottom: 8px; }
        .header p { opacity: 0.9; font-size: 14px; }
        .config-form {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .form-group {
            margin-bottom: 25px;
        }
        .form-label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #333;
        }
        .form-select {
            width: 100%;
            padding: 12px;
            font-size: 14px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            background: white;
        }
        .form-select:focus {
            outline: none;
            border-color: #07c160;
        }
        .option-desc {
            font-size: 13px;
            color: #666;
            margin-top: 5px;
        }
        .checkbox-group {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .checkbox-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .checkbox-item input[type="checkbox"] {
            width: 18px;
            height: 18px;
        }
        .checkbox-item label {
            font-size: 14px;
            color: #333;
        }
        .number-input {
            width: 80px;
            padding: 8px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
        }
        .save-btn {
            width: 100%;
            padding: 15px;
            background: #07c160;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 20px;
        }
        .save-btn:hover { background: #06ad56; }
        .section-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin: 30px 0 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }
        .back-link {
            display: inline-block;
            margin-top: 20px;
            color: #07c160;
            text-decoration: none;
        }
        .warning-box {
            background: #fff3e0;
            border-left: 4px solid #f57c00;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .warning-box p {
            color: #e65100;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚙️ 查询引擎配置</h1>
            <p>自定义召回策略、筛选策略和推送模式</p>
        </div>
        
        <div class="tabs" style="display: flex; gap: 10px; margin-bottom: 20px;">
            <a href="/query/config" style="padding: 10px 20px; background: #07c160; color: white; border-radius: 6px; text-decoration: none;">策略配置</a>
            <a href="/query/prompts" style="padding: 10px 20px; background: white; color: #666; border-radius: 6px; text-decoration: none;">Prompt配置</a>
        </div>
        
        <div class="config-form">
            <form method="POST">
                <div class="section-title">📥 召回策略 <small style="font-weight: normal; color: #666;">（如何从文章库找到候选文章）</small></div>
                <div class="form-group">
                    <label class="form-label">选择召回策略</label>
                    <select name="recall_strategy" class="form-select" onchange="showStrategyDetail('recall', this.value)">
                        {% for key, info in recall_strategies.items() %}
                        <option value="{{ key }}" {% if current_config.recall_strategy == key %}selected{% endif %}>
                            {{ info.name }}
                        </option>
                        {% endfor %}
                    </select>
                    <div id="recall-detail" class="strategy-detail">
                        <p class="option-desc"><strong>说明：</strong>{{ recall_strategies[current_config.recall_strategy].description }}</p>
                        <div class="detail-box">
                            <p><strong>工作原理：</strong></p>
                            <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; font-size: 12px; white-space: pre-wrap;">{{ recall_strategies[current_config.recall_strategy].how_it_works }}</pre>
                            <p style="margin-top: 10px;"><span style="color: #07c160;">✓ 优点：</span>{{ recall_strategies[current_config.recall_strategy].pros }}</p>
                            <p><span style="color: #f57c00;">✗ 缺点：</span>{{ recall_strategies[current_config.recall_strategy].cons }}</p>
                            <p style="margin-top: 10px; font-style: italic; color: #666;">💡 示例：{{ recall_strategies[current_config.recall_strategy].example }}</p>
                        </div>
                    </div>
                </div>
                
                <div class="section-title">🔍 筛选策略 <small style="font-weight: normal; color: #666;">（如何从候选中选出最终推荐）</small></div>
                <div class="form-group">
                    <label class="form-label">选择筛选策略</label>
                    <select name="filter_strategy" class="form-select" onchange="showStrategyDetail('filter', this.value)">
                        {% for key, info in filter_strategies.items() %}
                        <option value="{{ key }}" {% if current_config.filter_strategy == key %}selected{% endif %}>
                            {{ info.name }}
                        </option>
                        {% endfor %}
                    </select>
                    <div id="filter-detail" class="strategy-detail">
                        <p class="option-desc"><strong>说明：</strong>{{ filter_strategies[current_config.filter_strategy].description }}</p>
                        <div class="detail-box">
                            <p><strong>工作原理：</strong></p>
                            <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; font-size: 12px; white-space: pre-wrap;">{{ filter_strategies[current_config.filter_strategy].how_it_works }}</pre>
                            <p style="margin-top: 10px;"><span style="color: #07c160;">✓ 优点：</span>{{ filter_strategies[current_config.filter_strategy].pros }}</p>
                            <p><span style="color: #f57c00;">✗ 缺点：</span>{{ filter_strategies[current_config.filter_strategy].cons }}</p>
                            <p style="margin-top: 10px; font-style: italic; color: #666;">💡 示例：{{ filter_strategies[current_config.filter_strategy].example }}</p>
                        </div>
                    </div>
                </div>
                
                <div class="section-title">🚀 推送模式</div>
                <div class="form-group">
                    <label class="form-label">选择推送模式</label>
                    <select name="push_mode" class="form-select">
                        {% for key, info in push_modes.items() %}
                        <option value="{{ key }}" {% if current_config.push_mode == key %}selected{% endif %}>
                            {{ info.name }}
                        </option>
                        {% endfor %}
                    </select>
                    <p class="option-desc">
                        {{ push_modes[current_config.push_mode].description }}
                    </p>
                    {% if current_config.push_mode == 'auto_draft' %}
                    <div class="warning-box">
                        <p>⚠️ 警告：自动推送模式将直接修改微信草稿箱，请谨慎使用！</p>
                    </div>
                    {% endif %}
                </div>
                
                <div class="section-title">👁️ 显示选项</div>
                <div class="form-group">
                    <label class="form-label">查询结果展示</label>
                    <div class="checkbox-group">
                        <div class="checkbox-item">
                            <input type="checkbox" name="show_process" id="show_process" 
                                   {% if current_config.display.show_process %}checked{% endif %}>
                            <label for="show_process">显示匹配过程</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="show_candidates" id="show_candidates"
                                   {% if current_config.display.show_candidates %}checked{% endif %}>
                            <label for="show_candidates">显示候选列表</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="show_reason" id="show_reason"
                                   {% if current_config.display.show_reason %}checked{% endif %}>
                            <label for="show_reason">显示推荐理由</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="show_similar" id="show_similar"
                                   {% if current_config.display.show_similar %}checked{% endif %}>
                            <label for="show_similar">显示相似文章</label>
                        </div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label class="form-label">最大备选数</label>
                    <input type="number" name="max_alternatives" class="number-input"
                           value="{{ current_config.display.max_alternatives }}" min="0" max="5">
                </div>
                
                <button type="submit" class="save-btn">💾 保存配置</button>
            </form>
        </div>
        
        <a href="/query" class="back-link">← 返回查询页面</a>
    </div>
    
    <script>
        // 策略详情数据
        const strategies = {
            recall: {{ recall_strategies|tojson }},
            filter: {{ filter_strategies|tojson }}
        };
        
        function showStrategyDetail(type, key) {
            const info = strategies[type][key];
            if (!info) return;
            
            const detailDiv = document.getElementById(type + '-detail');
            detailDiv.innerHTML = `
                <p class="option-desc"><strong>说明：</strong>${info.description}</p>
                <div class="detail-box" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 10px;">
                    <p><strong>工作原理：</strong></p>
                    <pre style="background: white; padding: 10px; border-radius: 4px; font-size: 12px; white-space: pre-wrap; border: 1px solid #e0e0e0;">${info.how_it_works}</pre>
                    <p style="margin-top: 10px;"><span style="color: #07c160;">✓ 优点：</span>${info.pros}</p>
                    <p><span style="color: #f57c00;">✗ 缺点：</span>${info.cons}</p>
                    <p style="margin-top: 10px; font-style: italic; color: #666;">💡 示例：${info.example}</p>
                </div>
            `;
        }
    </script>
</body>
</html>
'''


# ==================== 主程序入口 ====================

if __name__ == '__main__':
    print("🚀 启动文章管理库 Web 服务")
    print(f"📚 管理地址: http://0.0.0.0:8080/library")
    print(f"🔍 查询地址: http://0.0.0.0:8080/query")
    print(f"⚙️  配置地址: http://0.0.0.0:8080/query/config")
    app.run(host='0.0.0.0', port=8080, debug=True)
