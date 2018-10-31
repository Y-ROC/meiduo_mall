from django.conf.urls import url
from rest_framework import routers
from rest_framework_jwt.views import obtain_jwt_token

from users.views import *

urlpatterns = [
    url(r'^sms_codes/(?P<mobile>1[3-9]\d{9})/$', SMSCodeView.as_view()),
    url(r'^usernames/(?P<username>\w{5,20})/count/$', UsernameCountView.as_view()),
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', MobileCountView.as_view()),
    url(r'^users/$', UserView.as_view()),
    url(r'^authorizations/$', obtain_jwt_token),
    url(r'^user/$', UserDetailView.as_view()),
    url(r'^emails/$', EmailView.as_view()),
    url(r'^emails/verification/', VerifyEmailView.as_view()),
    # url(r'^addresses/$', AddressView.as_view()),
    # url(r'^addresses/(?P<pk>\d+)/$', AddressView.as_view()),
    # url(r'^addresses/(?P<pk>\d+)/status/$', AddressView.as_view()),

]
router = routers.DefaultRouter()
router.register(r'addresses', AddressViewSet, base_name='addresses')

urlpatterns += router.urls