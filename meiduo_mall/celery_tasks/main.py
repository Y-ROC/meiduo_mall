import os

from celery import Celery

# 为celery使用django配置文件进行设置
if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'meiduo_mall.settings.dev'

# 创建celery应用
app = Celery('meiduo')

# 导入celery配置
app.config_from_object('celery_tasks.config')

# 自动注册celery任务
app.autodiscover_tasks(['celery_tasks.sms'])
