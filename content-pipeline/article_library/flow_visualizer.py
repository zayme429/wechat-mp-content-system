#!/usr/bin/env python3
"""
微信内容生产流程可视化模块
展示从主题到发布的完整流程状态
"""

from flask import Flask, render_template_string, jsonify
from datetime import datetime
import json

# 流程看板 HTML 模板
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>微信公众号内容生产流程看板</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
            background: #f0f2f5;
            color: #333;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        /* 头部 */
        .header {
            background: linear-gradient(135deg, #07c160 0%, #059e4c 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(7, 193, 96, 0.3);
        }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .status-bar {
            display: flex;
            gap: 30px;
            margin-top: 20px;
        }
        .status-item {
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 8px;
        }
        .status-label { font-size: 12px; opacity: 0.8; }
        .status-value { font-size: 20px; font-weight: bold; }
        
        /* 流程时间轴 */
        .flow-container {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            margin-bottom: 20px;
        }
        .flow-title {
            font-size: 18px;
            margin-bottom: 25px;
            padding-left: 12px;
            border-left: 4px solid #07c160;
        }
        
        /* 流程步骤 */
        .flow-steps {
            display: flex;
            justify-content: space-between;
            position: relative;
        }
        .flow-steps::before {
            content: '';
            position: absolute;
            top: 30px;
            left: 50px;
            right: 50px;
            height: 4px;
            background: #e8e8e8;
            z-index: 0;
        }
        .flow-step {
            flex: 1;
            text-align: center;
            position: relative;
            z-index: 1;
        }
        .step-icon {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: #f5f5f5;
            border: 3px solid #e8e8e8;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 15px;
            font-size: 24px;
            transition: all 0.3s;
        }
        .flow-step.active .step-icon {
            background: #07c160;
            border-color: #07c160;
            color: white;
            animation: pulse 2s infinite;
        }
        .flow-step.completed .step-icon {
            background: #07c160;
            border-color: #07c160;
            color: white;
        }
        .flow-step.error .step-icon {
            background: #ff4d4f;
            border-color: #ff4d4f;
            color: white;
        }
        .step-name {
            font-weight: 500;
            margin-bottom: 5px;
        }
        .step-status {
            font-size: 12px;
            color: #999;
        }
        .step-time {
            font-size: 11px;
            color: #ccc;
            margin-top: 5px;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        
        /* 实时日志 */
        .log-container {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            max-height: 300px;
            overflow-y: auto;
        }
        .log-line {
            margin-bottom: 5px;
            line-height: 1.5;
        }
        .log-time { color: #858585; }
        .log-info { color: #4ec9b0; }
        .log-success { color: #b5cea8; }
        .log-error { color: #f48771; }
        .log-warning { color: #dcdcaa; }
        
        /* 候选文章卡片 */
        .candidates-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .candidate-card {
            background: #f9f9f9;
            border: 2px solid transparent;
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s;
        }
        .candidate-card:hover {
            border-color: #07c160;
            transform: translateY(-2px);
        }
        .candidate-card.selected {
            border-color: #07c160;
            background: #f0f9f4;
        }
        .candidate-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 12px;
        }
        .candidate-num {
            background: #07c160;
            color: white;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
        }
        .candidate-score {
            font-size: 20px;
            font-weight: bold;
            color: #07c160;
        }
        .candidate-title {
            font-weight: 600;
            margin-bottom: 8px;
        }
        .candidate-angle {
            font-size: 13px;
            color: #666;
            margin-bottom: 10px;
        }
        .candidate-preview {
            font-size: 13px;
            color: #888;
            line-height: 1.6;
            max-height: 80px;
            overflow: hidden;
        }
        .candidate-actions {
            margin-top: 15px;
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 8px 16px;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #07c160;
            color: white;
        }
        .btn-secondary {
            background: #f0f0f0;
            color: #666;
        }
        
        /* 统计卡片 */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #07c160;
        }
        .stat-label {
            color: #666;
            font-size: 14px;
            margin-top: 5px;
        }
        
        /* 响应式 */
        @media (max-width: 768px) {
            .flow-steps {
                flex-direction: column;
                gap: 20px;
            }
            .flow-steps::before {
                display: none;
            }
            .candidates-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>🚀 微信公众号内容生产流程看板</h1>
            <p class="subtitle">实时监控文章生成、审核、发布全流程</p>
            
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-label">当前状态</div>
                    <div class="status-value" id="current-status">等待开始</div>
                </div>
                <div class="status-item">
                    <div class="status-label">当前主题</div>
                    <div class="status-value" id="current-topic">-</div>
                </div>
                <div class="status-item">
                    <div class="status-label">已耗时</div>
                    <div class="status-value" id="elapsed-time">00:00</div>
                </div>
            </div>
        </div>
        
        <!-- 统计 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="stat-total">0</div>
                <div class="stat-label">文章库总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-approved">0</div>
                <div class="stat-label">审核通过</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-candidates">0</div>
                <div class="stat-label">候选待审</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-published">0</div>
                <div class="stat-label">已发布</div>
            </div>
        </div>
        
        <!-- 流程时间轴 -->
        <div class="flow-container">
            <div class="flow-title">📋 生产流程</div>
            <div class="flow-steps" id="flow-steps">
                <div class="flow-step" data-step="1">
                    <div class="step-icon">🎯</div>
                    <div class="step-name">主题确定</div>
                    <div class="step-status">等待中</div>
                    <div class="step-time"></div>
                </div>
                <div class="flow-step" data-step="2">
                    <div class="step-icon">📚</div>
                    <div class="step-name">文献采集</div>
                    <div class="step-status">等待中</div>
                    <div class="step-time"></div>
                </div>
                <div class="flow-step" data-step="3">
                    <div class="step-icon">💡</div>
                    <div class="step-name">选题设计</div>
                    <div class="step-status">等待中</div>
                    <div class="step-time"></div>
                </div>
                <div class="flow-step" data-step="4">
                    <div class="step-icon">✍️</div>
                    <div class="step-name">文章生成</div>
                    <div class="step-status">等待中</div>
                    <div class="step-time"></div>
                </div>
                <div class="flow-step" data-step="5">
                    <div class="step-icon">📧</div>
                    <div class="step-name">审核通知</div>
                    <div class="step-status">等待中</div>
                    <div class="step-time"></div>
                </div>
                <div class="flow-step" data-step="6">
                    <div class="step-icon">✅</div>
                    <div class="step-name">审核完成</div>
                    <div class="step-status">等待中</div>
                    <div class="step-time"></div>
                </div>
            </div>
        </div>
        
        <!-- 候选文章 -->
        <div class="flow-container" id="candidates-section" style="display: none;">
            <div class="flow-title">📝 候选文章 (等待审核)</div>
            <div class="candidates-grid" id="candidates-list">
                <!-- 动态填充 -->
            </div>
        </div>
        
        <!-- 实时日志 -->
        <div class="flow-container">
            <div class="flow-title">📜 实时日志</div>
            <div class="log-container" id="log-container">
                <div class="log-line"><span class="log-time">[09:00:00]</span> 系统就绪，等待任务...</div>
            </div>
        </div>
    </div>
    
    <script>
        // 定时刷新状态
        function refreshStatus() {
            fetch('/api/flow-status')
                .then(r => r.json())
                .then(data => updateDashboard(data))
                .catch(e => console.error('刷新失败:', e));
        }
        
        function updateDashboard(data) {
            // 更新头部状态
            document.getElementById('current-status').textContent = data.status;
            document.getElementById('current-topic').textContent = data.topic || '-';
            document.getElementById('elapsed-time').textContent = data.elapsed_time;
            
            // 更新统计
            document.getElementById('stat-total').textContent = data.stats.total;
            document.getElementById('stat-approved').textContent = data.stats.approved;
            document.getElementById('stat-candidates').textContent = data.stats.candidates;
            document.getElementById('stat-published').textContent = data.stats.published;
            
            // 更新流程步骤
            data.steps.forEach((step, index) => {
                const stepEl = document.querySelector(`[data-step="${index + 1}"]`);
                if (stepEl) {
                    stepEl.className = 'flow-step ' + step.state;
                    stepEl.querySelector('.step-status').textContent = step.status_text;
                    if (step.time) {
                        stepEl.querySelector('.step-time').textContent = step.time;
                    }
                }
            });
            
            // 更新候选文章
            if (data.candidates && data.candidates.length > 0) {
                document.getElementById('candidates-section').style.display = 'block';
                const container = document.getElementById('candidates-list');
                container.innerHTML = data.candidates.map((c, i) => `
                    <div class="candidate-card ${c.selected ? 'selected' : ''}">
                        <div class="candidate-header">
                            <div class="candidate-num">${i + 1}</div>
                            <div class="candidate-score">${c.score.toFixed(1)}</div>
                        </div>
                        <div class="candidate-title">${c.title}</div>
                        <div class="candidate-angle">${c.angle}</div>
                        <div class="candidate-preview">${c.preview}</div>
                        <div class="candidate-actions">
                            <button class="btn btn-primary" onclick="selectCandidate('${c.id}')">选择</button>
                            <button class="btn btn-secondary" onclick="previewCandidate('${c.id}')">预览</button>
                        </div>
                    </div>
                `).join('');
            }
            
            // 更新日志
            if (data.logs && data.logs.length > 0) {
                const logContainer = document.getElementById('log-container');
                logContainer.innerHTML = data.logs.map(log => `
                    <div class="log-line">
                        <span class="log-time">[${log.time}]</span>
                        <span class="log-${log.level}">${log.message}</span>
                    </div>
                `).join('');
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        }
        
        // 每3秒刷新一次
        setInterval(refreshStatus, 3000);
        refreshStatus();
        
        // 候选操作
        function selectCandidate(id) {
            fetch(`/api/select-candidate/${id}`, {method: 'POST'})
                .then(r => r.json())
                .then(data => alert(data.message));
        }
        
        function previewCandidate(id) {
            window.open(`/article/preview/${id}`, '_blank');
        }
    </script>
</body>
</html>
'''

class FlowVisualizer:
    """流程可视化器"""
    
    def __init__(self):
        self.current_flow = {
            'status': 'idle',
            'topic': None,
            'start_time': None,
            'current_step': 0,
            'steps': [
                {'name': '主题确定', 'state': 'pending', 'status_text': '等待中', 'time': None},
                {'name': '文献采集', 'state': 'pending', 'status_text': '等待中', 'time': None},
                {'name': '选题设计', 'state': 'pending', 'status_text': '等待中', 'time': None},
                {'name': '文章生成', 'state': 'pending', 'status_text': '等待中', 'time': None},
                {'name': '审核通知', 'state': 'pending', 'status_text': '等待中', 'time': None},
                {'name': '审核完成', 'state': 'pending', 'status_text': '等待中', 'time': None},
            ],
            'candidates': [],
            'logs': []
        }
    
    def start_flow(self, topic: str):
        """开始新流程"""
        from datetime import datetime
        self.current_flow = {
            'status': 'running',
            'topic': topic,
            'start_time': datetime.now(),
            'current_step': 0,
            'steps': [
                {'name': '主题确定', 'state': 'completed', 'status_text': '已完成', 'time': datetime.now().strftime('%H:%M:%S')},
                {'name': '文献采集', 'state': 'active', 'status_text': '进行中...', 'time': None},
                {'name': '选题设计', 'state': 'pending', 'status_text': '等待中', 'time': None},
                {'name': '文章生成', 'state': 'pending', 'status_text': '等待中', 'time': None},
                {'name': '审核通知', 'state': 'pending', 'status_text': '等待中', 'time': None},
                {'name': '审核完成', 'state': 'pending', 'status_text': '等待中', 'time': None},
            ],
            'candidates': [],
            'logs': [{'time': datetime.now().strftime('%H:%M:%S'), 'level': 'info', 'message': f'开始生成文章: {topic}'}]
        }
    
    def update_step(self, step_index: int, state: str, status_text: str):
        """更新步骤状态"""
        from datetime import datetime
        if 0 <= step_index < len(self.current_flow['steps']):
            self.current_flow['steps'][step_index]['state'] = state
            self.current_flow['steps'][step_index]['status_text'] = status_text
            self.current_flow['steps'][step_index]['time'] = datetime.now().strftime('%H:%M:%S')
            self.current_flow['current_step'] = step_index
            
            # 标记之前的步骤为完成
            for i in range(step_index):
                if self.current_flow['steps'][i]['state'] == 'pending':
                    self.current_flow['steps'][i]['state'] = 'completed'
                    self.current_flow['steps'][i]['status_text'] = '已完成'
    
    def add_log(self, message: str, level: str = 'info'):
        """添加日志"""
        from datetime import datetime
        self.current_flow['logs'].append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'level': level,
            'message': message
        })
        # 只保留最近50条
        self.current_flow['logs'] = self.current_flow['logs'][-50:]
    
    def set_candidates(self, candidates: list):
        """设置候选文章"""
        self.current_flow['candidates'] = candidates
    
    def get_status(self) -> dict:
        """获取当前状态"""
        from datetime import datetime
        
        # 计算已耗时
        elapsed = '00:00'
        if self.current_flow['start_time']:
            delta = datetime.now() - self.current_flow['start_time']
            elapsed = f"{delta.seconds // 60:02d}:{delta.seconds % 60:02d}"
        
        return {
            **self.current_flow,
            'elapsed_time': elapsed,
            'stats': {
                'total': 0,
                'approved': 0,
                'candidates': len(self.current_flow['candidates']),
                'published': 0
            }
        }


# 使用示例
if __name__ == '__main__':
    from flask import Flask
    
    app = Flask(__name__)
    visualizer = FlowVisualizer()
    
    @app.route('/dashboard')
    def dashboard():
        return render_template_string(DASHBOARD_TEMPLATE)
    
    @app.route('/api/flow-status')
    def flow_status():
        return jsonify(visualizer.get_status())
    
    print("流程可视化演示")
    print("访问: http://localhost:5000/dashboard")
    
    # 模拟流程
    import time
    import threading
    
    def simulate_flow():
        time.sleep(2)
        visualizer.start_flow("AI学习方法论")
        
        for i in range(1, 6):
            time.sleep(2)
            visualizer.update_step(i, 'active', '进行中...')
            visualizer.add_log(f'步骤 {i} 进行中...')
            
            time.sleep(2)
            visualizer.update_step(i, 'completed', '已完成')
            visualizer.add_log(f'步骤 {i} 完成', 'success')
        
        # 添加候选
        visualizer.set_candidates([
            {'id': '1', 'title': 'AI时代的学习革命', 'angle': '实战派', 'score': 8.5, 'preview': '这是一篇关于...', 'selected': False},
            {'id': '2', 'title': '认知升级之路', 'angle': '深度派', 'score': 8.2, 'preview': '深度分析...', 'selected': True},
            {'id': '3', 'title': '从0到1掌握AI', 'angle': '故事派', 'score': 7.8, 'preview': '故事讲述...', 'selected': False},
        ])
    
    threading.Thread(target=simulate_flow).start()
    app.run(debug=True, port=5000)
