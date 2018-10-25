from django.conf.urls import url

from users.views import *

urlpatterns = [
    url(r'^sms_codes/(?P<mobile>1[3-9]\d{9})$', SMSCodeView.as_view()),
    url(r'^usernames/(?P<username>\w{5,20})/count/$', UsernameCountView.as_view()),

]
