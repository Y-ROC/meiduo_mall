from random import randint

from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from celery_tasks.sms.tasks import send_sms_code
from users.models import User
from users.serializers import CreateUserSerializer, UserDetailSerializer, EmailSerializer


class SMSCodeView(APIView):
    """发送短信验证码"""

    def get(self, request, mobile):
        # 创建连接到Redis的对象
        conn = get_redis_connection('verify')
        # 60秒内不允许重发发送短信
        send_flag = conn.get('send_flag_%s' % mobile)
        if send_flag:
            return Response({"message": "发送短信过于频繁"}, status=status.HTTP_400_BAD_REQUEST)
        # 生成一个短信验证码
        sms_code = '%06d' % randint(0, 999999)
        print(sms_code)
        # 保存短信验证码,redis管道pipeline的使用
        pl = conn.pipeline()
        pl.setex('sms_%s' % mobile, 300, sms_code)
        pl.setex('send_flag_%s' % mobile, 60, 1)
        pl.execute()
        # 发送短信验证码
        send_sms_code.delay(mobile, sms_code, 1)
        # 返回结果
        return Response({"message": "OK"})


class UsernameCountView(APIView):
    """
    用户名数量
    """

    def get(self, request, username):
        count = User.objects.filter(username=username).count()
        data = {
            'username': username,
            'count': count,
        }
        return Response(data)


class MobileCountView(APIView):
    """
    获取指定手机号数量
    """

    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()
        data = {
            'mobile': mobile,
            'count': count
        }
        return Response(data)


class UserView(CreateAPIView):
    """
    用户注册
    """
    serializer_class = CreateUserSerializer


class UserDetailView(APIView):
    """
    用户详情
    """

    def get(self, request):
        user = request.user
        serializer = UserDetailSerializer(user)
        return Response(serializer.data)


class EmailView(UpdateAPIView):
    """邮箱保存及邮件发送"""
    serializer_class = EmailSerializer

    def get_object(self):
        return self.request.user


class VerifyEmailView(APIView):
    """验证邮箱"""

    def get(self, request):
        # 获取token
        token = request.query_params.get('token')
        if not token:
            return Response({'message': '缺少token'}, status=status.HTTP_400_BAD_REQUEST)
        # 验证token
        user = User.check_verify_email_token(token)
        if user is None:
            return Response({'message': '链接信息无效'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user.email_active = True
            user.save()
            return Response({"message": "OK"})
