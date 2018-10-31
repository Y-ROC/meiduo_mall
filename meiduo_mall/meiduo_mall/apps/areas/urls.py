from django.conf.urls import url, include

from . import views

urlpatterns = [
    url(r'^areas/$', views.AreaView.as_view()),
    url(r'^areas/(?P<pk>\d+)/$', views.SubAreaView.as_view()),
]