# 邮件可视化 HTML 模板示例

MAIL_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
<style>
.progress-bar { width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #07c160, #059e4c); transition: width 0.5s; }
.candidate-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin: 10px 0; }
.candidate-card:hover { border-color: #07c160; }
.score-badge { background: #07c160; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; }
.btn { display: inline-block; background: #07c160; color: white; padding: 8px 20px; 
       text-decoration: none; border-radius: 4px; margin: 5px; }
</style>
</head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">

<h2>📝 新文章候选已生成</h2>

<!-- 进度可视化 -->
<div style="margin: 20px 0;">
    <p style="color: #666; font-size: 14px;">生成进度</p>
    <div class="progress-bar">
        <div class="progress-fill" style="width: 100%;"></div>
    </div>
    <p style="text-align: center; color: #07c160; font-size: 12px;">✓ 已完成</p>
</div>

<!-- 候选对比 -->
<h3>候选文章（请点击查看全文后回复选择）</h3>

<div class="candidate-card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h4 style="margin: 0;">候选1：AI时代的学习革命</h4>
        <span class="score-badge">质量分 8.5</span>
    </div>
    <p style="color: #666; font-size: 13px;">🎯 实战派角度：给出具体可执行的AI学习步骤</p>
    <p style="color: #888; font-size: 12px;">预览：在这篇文章中，我将分享一套经过验证的AI学习方法论...</p>
    <div style="margin-top: 10px;">
        <a href="http://154.9.252.35:8080/article/abc123" class="btn">📖 查看全文</a>
        <a href="mailto:ai@openclaw.ai?subject=选择候选1&body=我选择候选1" class="btn" style="background: #ff9500;">✓ 选择这篇</a>
    </div>
</div>

<!-- 流程状态 -->
<div style="background: #f9f9f9; padding: 15px; border-radius: 8px; margin-top: 20px;">
    <p style="margin: 0; color: #666; font-size: 13px;">
        📊 生成统计：主题分析 ✓ | 文献采集 ✓ | 选题设计 ✓ | 文章生成 ✓ | 等待审核 ○
    </p>
</div>

<p style="color: #999; font-size: 12px; margin-top: 30px;">
    回复 "选候选1/2/3" 即可标记审核状态 | 
    <a href="http://154.9.252.35:8080/library">查看文章库</a>
</p>

</body>
</html>
'''
