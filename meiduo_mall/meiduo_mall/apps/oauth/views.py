from django.conf import settings
from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from QQLoginTool.QQtool import OAuthQQ
from rest_framework_jwt.settings import api_settings

from carts.utils import merge_cart_cookie_to_redis
from oauth.models import OAuthQQUser
from oauth.serializers import QQAuthUserSerializer
from oauth.utils import generate_save_user_token


class QQAuthURLView(APIView):
    def get(self, request):
        # 获取state
        state = request.query_params.get('state', '/')
        # QQ对象
        qq = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                     redirect_uri=settings.QQ_REDIRECT_URI, state=state)
        # 调用QQ对象生成跳转连接
        login_url = qq.get_qq_url()
        # 返回跳转链接
        return Response({"login_url": login_url})


class QQAuthUserView(GenericAPIView):
    """用户扫码登录的回调处理"""
    # 指定序列化器
    serializer_class = QQAuthUserSerializer

    def get(self, request):
        # 提取code请求参数
        code = request.query_params.get('code')
        if not code:
            return Response({'message': '缺少code'}, status=status.HTTP_400_BAD_REQUEST)
        # QQ对象
        qq = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                     redirect_uri=settings.QQ_REDIRECT_URI)
        try:
            # 使用code向QQ服务器请求access_code
            access_token = qq.get_access_token(code)
            # 使用access_token向QQ服务器请求openid
            openid = qq.get_open_id(access_token)
        except Exception:
            return Response({'message': 'QQ服务异常'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            # 使用openid查询该QQ用户是否在美多商城中绑定过用户
        try:
            oauth_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 如果openid没绑定美多商城用户，创建用户并绑定到openid
            # 为了能够在后续的绑定用户操作中前端可以使用openid，在这里将openid签名后响应给前端
            access_token_openid = generate_save_user_token(openid)
            return Response({'access_token': access_token_openid})
        else:
            # 如果openid已绑定美多商城用户，直接生成JWT token，并返回
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

            # 获取oauth_user关联的user
            user = oauth_user.user
            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)

            response = Response({
                'token': token,
                'user_id': user.id,
                'username': user.username
            })
            # 合并购物车
            response = merge_cart_cookie_to_redis(request, user, response)
            return response

    def post(self, request):
        """openid绑定到用户"""

        # 获取序列化器对象
        serializer = self.get_serializer(data=request.data)
        # 开启校验
        serializer.is_valid(raise_exception=True)
        # 保存校验结果，并接收
        user = serializer.save()

        # 生成JWT token，并响应
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        response = Response({
            'token': token,
            'user_id': user.id,
            'username': user.username
        })
        # 合并购物车
        response = merge_cart_cookie_to_redis(request, user, response)
        return response
