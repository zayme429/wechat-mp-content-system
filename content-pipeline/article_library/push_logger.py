import logging
import os
from datetime import datetime

# 创建日志目录
log_dir = '/root/.openclaw/workspace/content-pipeline/logs'
os.makedirs(log_dir, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{log_dir}/push.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('wechat_push')

def log_push_start(article_id, title):
    """记录推送开始"""
    logger.info(f"[PUSH_START] article_id={article_id}, title={title[:50]}")

def log_push_step(step, message, data=None):
    """记录推送步骤"""
    logger.info(f"[PUSH_STEP] {step}: {message}")
    if data:
        logger.info(f"  Data: {data}")

def log_push_error(error, traceback=None):
    """记录推送错误"""
    logger.error(f"[PUSH_ERROR] {error}")
    if traceback:
        logger.error(f"  Traceback: {traceback}")

def log_push_success(media_id):
    """记录推送成功"""
    logger.info(f"[PUSH_SUCCESS] media_id={media_id}")
