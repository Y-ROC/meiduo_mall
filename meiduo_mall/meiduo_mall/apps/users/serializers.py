import re

from django_redis import get_redis_connection
from rest_framework import serializers
from celery_tasks.email.tasks import send_verify_email
from users.models import User, Address


class CreateUserSerializer(serializers.ModelSerializer):
    """
    创建用户序列化器
    """
    password2 = serializers.CharField(label="确认密码", write_only=True)
    sms_code = serializers.CharField(label="短信验证码", write_only=True)
    allow = serializers.CharField(label="同意协议", write_only=True)
    # 添加token字段
    token = serializers.CharField(label='令牌', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'password2', 'sms_code', 'mobile', 'allow', 'token')

    extra_kwargs = {
        "username": {
            "min_length": 5,
            "max_length": 20,
            "error_messages": {
                "min_length": "仅允许5-20个字符的用户名",
                "max_length": "仅允许5-20个字符的用户名",
            }
        },
        "password": {
            "write_only": True,
            "min_length": 8,
            "max_length": 20,
            "error_messages": {
                "min_length": "仅允许8-20个字符的密码",
                "max_length": "仅允许8-20个字符的密码",
            }
        }
    }

    def validate_mobile(self, value):
        """验证手机号码"""
        if not re.match(r"1[1-9]\d{9}", value):
            raise serializers.ValidationError("手机号码格式错误")
        return value

    def validate_allow(self, value):
        if value != 'true':
            raise serializers.ValidationError('请同意用户协议')
        return value

    def validate(self, attrs):
        # 判断两次密码
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError('两次密码不一致')
        # 判断短信验证码
        conn = get_redis_connection("verify")
        mobile = attrs['mobile']
        real_sms_code = conn.get('sms_%s' % mobile)
        if real_sms_code is None:
            raise serializers.ValidationError('无效的短信验证码')
        if attrs['sms_code'] != real_sms_code.decode():
            raise serializers.ValidationError("短信验证码错误")
        return attrs

    def create(self, validate_data):
        """创建用户"""
        # 移除数据库模型中不存在的属性
        del validate_data['password2']
        del validate_data['sms_code']
        del validate_data['allow']
        user = super().create(validate_data)
        # 调用Django的认证系统加密密码
        user.set_password(validate_data["password"])
        user.save()
        # 生成token
        from rest_framework_jwt.settings import api_settings

        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        user.token = token
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """
    用户详细信息序列化器
    """

    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'email', 'email_active')


class EmailSerializer(serializers.ModelSerializer):
    """邮箱信息序列化器"""

    class Meta:
        model = User
        fields = ('email',)

    def update(self, instance, validated_data):
        instance.email = validated_data['email']
        instance.save()
        # 生成验证链接
        verify_url = instance.generate_verify_email_url()
        # 发送验证邮件
        send_verify_email.delay(validated_data['email'], verify_url)
        return instance


class UserAddressSerializer(serializers.ModelSerializer):
    """地址信息序列化器"""
    # 序列化输出
    province = serializers.StringRelatedField(label='省', read_only=True)
    city = serializers.StringRelatedField(label='市', read_only=True)
    district = serializers.StringRelatedField(label='区', read_only=True)
    # 序列化输入
    province_id = serializers.IntegerField(label='省', write_only=True)
    city_id = serializers.IntegerField(label='市', write_only=True)
    district_id = serializers.IntegerField(label='区', write_only=True)

    class Meta:
        model = Address
        exclude = ('user', 'is_deleted', 'update_time', 'create_time')

    def validate_mobile(self, value):
        """验证手机号码"""
        if not re.match(r"1[1-9]\d{9}", value):
            raise serializers.ValidationError("手机号码格式错误")
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AddressTitleSerializer(serializers.ModelSerializer):
    """
    地址标题
    """
    class Meta:
        model = Address
        fields = ('title',)
