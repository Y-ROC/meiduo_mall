import os

from celery import Celery

# 为celery使用django配置文件进行设置
if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'meiduo_mall.settings.dev'

# 创建celery应用
app = Celery('meiduo', broker='redis://localhost:6379')

# 导入celery配置
app.config_from_object('celery_tasks.config')

# 自动注册celery任务
app.autodiscover_tasks(['celery_tasks.sms', 'celery_tasks.email'])
# linux
# 终端启动celery服务  -l info  查看启动后的详情信息
# celery -A celery_tasks.main worker -l info

# celery 原理：Worker 作为任务执行者 找到任务队列中所对应的任务 调用send_sms_code任务方法.delay()  通知worker执行 send_sms_code
# Django中需要做到：1.创建celery应用对象 2.定义相应的任务 3.通知celery对象delay调用方法 将任务加入到队列中等待被执行

# windows
# celery -A celery_tasks.main worker -l info --pool=solo
