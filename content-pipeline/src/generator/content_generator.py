#!/usr/bin/env python3
"""
LLM内容生成器 - 调用Kimi生成文章
"""

import os
import json
import requests
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ContentGenerator:
    def __init__(self):
        # 从OpenClaw配置读取API key/baseUrl（优先Claude，其次Kimi）
        provider = self._load_provider()
        self.api_key = provider.get('apiKey')

        # 非 gateway 的大模型请求：按你的要求统一走 Kimi（Moonshot OpenAI 协议）
        # 优先级：环境变量 > openclaw.json moonshot > 默认 moonshot
        self.base_url = (
            os.environ.get('KIMI_BASE_URL')
            or os.environ.get('CLAUDE_BASE_URL')
            or provider.get('baseUrl')
            or 'https://api.moonshot.cn/v1'
        )
        self.model = os.environ.get('KIMI_MODEL') or os.environ.get('CLAUDE_MODEL') or 'moonshot-v1-8k'
        
    def _load_provider(self):
        """从环境变量 / OpenClaw 配置读取 provider 信息（apiKey/baseUrl）。

        说明：本项目的 LLM 调用使用 OpenAI 兼容的 `/chat/completions`。
        最稳定的方式是直接调用本机 OpenClaw Gateway（它会按 openclaw.json 的模型路由到云驿/Claude）。
        """
        # 优先环境变量（允许显式指定 Kimi/Moonshot）
        api_key = os.environ.get('KIMI_API_KEY') or os.environ.get('MOONSHOT_API_KEY')
        base_url = os.environ.get('KIMI_BASE_URL')
        if api_key:
            return {"apiKey": api_key, "baseUrl": base_url}

        # 回退：从 OpenClaw 配置读取 moonshot provider
        try:
            config_path = Path.home() / '.openclaw' / 'openclaw.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            providers = config.get('models', {}).get('providers', {})
            if 'moonshot' in providers:
                p = providers['moonshot'] or {}
                return {"apiKey": p.get('apiKey'), "baseUrl": p.get('baseUrl')}
        except Exception:
            pass

        return {"apiKey": None, "baseUrl": None}
    
    def _call_llm(self, prompt, temperature=0.7, system_prompt: str = None):
        """调用LLM API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            if system_prompt is None:
                system_prompt = '你是一位资深的科技专栏作家，专注于AI时代的个人成长与职业发展。'

            data = {
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': temperature,
                'max_tokens': 4000
            }
            
            logger.info("🤖 调用LLM生成内容...")
            url = f'{self.base_url}/chat/completions'
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=300,
            )

            try:
                result = response.json()
            except Exception:
                logger.error(
                    "❌ API返回非JSON响应: %s %s %s",
                    response.status_code,
                    response.headers.get('content-type'),
                    response.text[:500],
                )
                raise
            
            # 检查错误
            if 'error' in result:
                logger.error(f"❌ API返回错误: {result['error']}")
                raise Exception(f"API Error: {result['error']}")
            
            if 'choices' not in result:
                logger.error(f"❌  unexpected response: {json.dumps(result, ensure_ascii=False)[:800]}")
                raise KeyError("'choices' not in response")

            content = result['choices'][0]['message']['content']
            logger.info("✅ LLM生成完成")
            return content
            
        except Exception as e:
            logger.error(f"❌ LLM调用失败: {e}")
            raise
    
    def analyze_topic(self, news_items, recent_topics):
        """分析选题角度"""
        logger.info("=== AI分析选题 ===")
        
        # 加载简化提示词
        prompt_path = Path('/root/.openclaw/workspace/content-pipeline/config/prompts/analyze_topic_simple.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        # 准备新闻内容
        news_text = ""
        for i, item in enumerate(news_items[:5], 1):
            news_text += f"\n{i}. {item['title']}\n   来源: {item['source']}\n"
        
        # 准备历史主题
        topics_text = ", ".join(recent_topics[-5:]) if recent_topics else "无"
        
        # 替换模板变量
        prompt = prompt_template.replace('{news_items}', news_text).replace('{recent_topics}', topics_text)
        
        # 调用LLM
        response = self._call_llm(prompt, temperature=0.8)
        
        # 解析文本结果
        try:
            lines = response.strip().split('\n')
            result = {'title': '', 'angle': '', 'target': '', 'value': ''}
            
            for line in lines:
                if '选题标题：' in line or '选题标题:' in line:
                    result['title'] = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                elif '核心角度：' in line or '核心角度:' in line:
                    result['angle'] = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                elif '目标读者：' in line or '目标读者:' in line:
                    result['target'] = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                elif '价值点：' in line or '价值点:' in line:
                    result['value'] = line.split('：', 1)[-1].split(':', 1)[-1].strip()
            
            # 如果没解析到标题，用第一行
            if not result['title'] and lines:
                result['title'] = lines[0][:50]
            
            logger.info(f"✅ 选题分析完成: {result['title'][:40]}...")
            return result
            
        except Exception as e:
            logger.error(f"❌ 解析分析结果失败: {e}")
            # 返回默认结果
            return {'title': 'AI时代的学习与成长', 'angle': '从被动接受到主动学习', 'target': '职场人士', 'value': '掌握AI时代的学习方法'}
    
    def write_article(self, topic_info):
        """撰写文章"""
        logger.info("=== AI撰写文章 ===")
        
        # 加载简化提示词
        prompt_path = Path('/root/.openclaw/workspace/content-pipeline/config/prompts/write_article_simple.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        # 替换模板变量
        prompt = (prompt_template
            .replace('{article_title}', topic_info.get('title', 'AI时代的学习与成长'))
            .replace('{core_angle}', topic_info.get('angle', topic_info.get('value', '深入分析AI时代的变化')))
            .replace('{target_audience}', topic_info.get('target', '职场人士')))
        
        # 调用LLM
        article = self._call_llm(prompt, temperature=0.7)
        
        logger.info(f"✅ 文章撰写完成，长度: {len(article)} 字符")
        return article

if __name__ == '__main__':
    # 测试
    gen = ContentGenerator()
    
    # 测试选题分析
    test_news = [
        {'title': 'ChatGPT发布新功能', 'summary': 'OpenAI发布...', 'source': '机器之心'}
    ]
    analysis = gen.analyze_topic(test_news, [])
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
