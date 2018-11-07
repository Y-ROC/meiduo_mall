from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^cart/$', views.CartView.as_view()),

]
