#!/usr/bin/env python3
"""
微信公众号直接发布脚本
基于 wechatpy 库，支持创建草稿后直接发布
"""

import os
import sys
import json
import requests
from pathlib import Path

# 微信 API 基础地址
WX_API_BASE = "https://api.weixin.qq.com/cgi-bin"

def get_access_token(app_id, app_secret):
    """获取 access_token"""
    url = f"{WX_API_BASE}/token"
    params = {
        "grant_type": "client_credential",
        "appid": app_id,
        "secret": app_secret
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    if "access_token" in data:
        return data["access_token"]
    else:
        print(f"❌ 获取 access_token 失败: {data}")
        sys.exit(1)

def upload_image(access_token, image_path):
    """上传图片到微信图床"""
    url = f"{WX_API_BASE}/media/uploadimg?access_token={access_token}"
    
    # 如果是网络图片，先下载
    if image_path.startswith('http'):
        import tempfile
        r = requests.get(image_path)
        suffix = Path(image_path).suffix or '.jpg'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(r.content)
            image_path = f.name
    
    with open(image_path, 'rb') as f:
        files = {'media': f}
        resp = requests.post(url, files=files)
    
    data = resp.json()
    if 'url' in data:
        return data['url']
    else:
        print(f"⚠️ 图片上传失败: {data}")
        return None

def create_draft(access_token, title, content, thumb_media_id=None):
    """创建图文消息草稿"""
    url = f"{WX_API_BASE}/draft/add?access_token={access_token}"
    
    articles = [{
        "title": title,
        "content": content,
        "need_open_comment": 1,
        "only_fans_can_comment": 0
    }]
    
    if thumb_media_id:
        articles[0]["thumb_media_id"] = thumb_media_id
    
    data = {"articles": articles}
    resp = requests.post(url, json=data)
    result = resp.json()
    
    if 'media_id' in result:
        return result['media_id']
    else:
        print(f"❌ 创建草稿失败: {result}")
        sys.exit(1)

def submit_publish(access_token, media_id):
    """提交发布（直接发布，不经过草稿箱审核）"""
    url = f"{WX_API_BASE}/freepublish/submit?access_token={access_token}"
    data = {"media_id": media_id}
    resp = requests.post(url, json=data)
    result = resp.json()
    
    if result.get('errcode') == 0:
        return result.get('publish_id')
    else:
        print(f"❌ 发布失败: {result}")
        sys.exit(1)

def get_publish_status(access_token, publish_id):
    """查询发布状态"""
    url = f"{WX_API_BASE}/freepublish/get?access_token={access_token}"
    data = {"publish_id": publish_id}
    resp = requests.post(url, json=data)
    return resp.json()

def main():
    # 读取配置
    app_id = os.environ.get('WECHAT_APP_ID')
    app_secret = os.environ.get('WECHAT_APP_SECRET')
    
    if not app_id or not app_secret:
        # 尝试从配置文件读取
        config_path = Path.home() / '.wechatmp' / 'config.json'
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                app_id = config.get('app_id')
                app_secret = config.get('app_secret')
    
    if not app_id or not app_secret:
        print("❌ 请先设置微信公众号凭证")
        print("环境变量: WECHAT_APP_ID, WECHAT_APP_SECRET")
        print("或配置文件: ~/.wechatmp/config.json")
        sys.exit(1)
    
    # 获取参数
    if len(sys.argv) < 3:
        print("用法: python publish_direct.py <标题> <内容文件或HTML内容> [封面图片路径]")
        print("示例: python publish_direct.py '文章标题' article.html")
        sys.exit(1)
    
    title = sys.argv[1]
    content_arg = sys.argv[2]
    cover_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    # 读取内容
    if os.path.isfile(content_arg):
        with open(content_arg, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = content_arg
    
    print(f"📝 正在发布: {title}")
    
    # 获取 access_token
    print("🔑 获取 access_token...")
    access_token = get_access_token(app_id, app_secret)
    print("✅ 获取成功")
    
    # 上传封面图（如果有）
    thumb_media_id = None
    if cover_path:
        print(f"📸 上传封面图...")
        # 先上传为永久素材
        url = f"{WX_API_BASE}/material/add_material?access_token={access_token}&type=thumb"
        with open(cover_path, 'rb') as f:
            files = {'media': f}
            resp = requests.post(url, files=files)
        result = resp.json()
        if 'media_id' in result:
            thumb_media_id = result['media_id']
            print("✅ 封面上传成功")
    
    # 创建草稿
    print("📄 创建草稿...")
    media_id = create_draft(access_token, title, content, thumb_media_id)
    print(f"✅ 草稿创建成功: {media_id}")
    
    # 直接发布
    print("🚀 提交发布...")
    publish_id = submit_publish(access_token, media_id)
    print(f"✅ 发布已提交，publish_id: {publish_id}")
    
    # 查询状态
    print("⏳ 查询发布状态...")
    status = get_publish_status(access_token, publish_id)
    print(f"📊 状态: {status}")
    
    print("\n✅ 文章已直接发布！")
    print("📱 前往公众号查看: https://mp.weixin.qq.com/")

if __name__ == '__main__':
    main()
