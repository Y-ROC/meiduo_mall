from random import randint

from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView, UpdateAPIView, ListCreateAPIView, GenericAPIView
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from celery_tasks.sms.tasks import send_sms_code
from goods.models import SKU
from goods.serializers import SKUSerializer
from meiduo_mall import constants
from users.models import User, Address
from users.serializers import CreateUserSerializer, UserDetailSerializer, EmailSerializer, UserAddressSerializer, \
    AddressTitleSerializer, AddUserBrowsingHistorySerializer


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


# class AddressView(ListCreateAPIView, UpdateAPIView):
#     serializer_class = UserAddressSerializer
#
#     def get_queryset(self):
#         return Address.objects.filter(user=self.request.user, is_deleted=False)
#
#     def delete(self, request, pk):
#         address = self.get_object()
#         address.is_deleted = True
#         address.save()
#         return Response({"message": "OK"})
#
#
# class StatusView(GenericAPIView):
#
#     def put(self, request, pk):
#         user = self.request.user
#         user.default_address_id = pk
#         user.save()
#         return Response({"id": pk})


class AddressViewSet(CreateModelMixin, UpdateModelMixin, GenericViewSet):
    """用户地址新增与修改"""
    serializer_class = UserAddressSerializer

    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)

    # GET /addresses/
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        user = self.request.user
        return Response({
            "user_id": user.id,
            "addresses": serializer.data,
            "limit": constants.USER_ADDRESS_COUNTS_LIMIT,
            "default_address_id": user.default_address_id,
        })

    # POST /addresses/
    def create(self, request, *args, **kwargs):
        """
        保存用户地址数据
        """
        # 检查用户地址数据数目不能超过上限
        count = request.user.addresses.filter(is_deleted=False).count()
        if count >= constants.USER_ADDRESS_COUNTS_LIMIT:
            return Response({'message': '保存地址数据已达到上限'}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

    # delete /addresses/<pk>/
    def destroy(self, request, *args, **kwargs):
        """
        处理删除
        """
        address = self.get_object()

        # 进行逻辑删除
        address.is_deleted = True
        address.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    # put /addresses/pk/status/
    @action(methods=['put'], detail=True)
    def status(self, request, pk=None):
        """
        设置默认地址
        """
        address = self.get_object()
        request.user.default_address = address
        request.user.save()
        return Response({'message': 'OK'}, status=status.HTTP_200_OK)

    # put /addresses/pk/title/
    # 需要请求体参数 title
    @action(methods=['put'], detail=True)
    def title(self, request, pk=None):
        """
        修改标题
        """
        address = self.get_object()
        serializer = AddressTitleSerializer(instance=address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserBrowsingHistoryView(CreateAPIView):
    """
    用户浏览历史记录
    """
    serializer_class = AddUserBrowsingHistorySerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        获取
        """
        user_id = request.user.id

        redis_conn = get_redis_connection("history")
        history = redis_conn.lrange("history_%s" % user_id, 0, constants.USER_BROWSING_HISTORY_COUNTS_LIMIT - 1)
        skus = []
        # 为了保持查询出的顺序与用户的浏览历史保存顺序一致
        for sku_id in history:
            sku = SKU.objects.get(id=sku_id)
            skus.append(sku)

        s = SKUSerializer(skus, many=True)
        return Response(s.data)
