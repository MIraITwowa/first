# userapp/serializers.py
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from userapp.models import Address, RealName


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    # 将默认的 username 字段改为 account
    account = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        authenticate_kwargs = {
            'account': attrs['account'],
            'password': attrs['password'],
        }
        user = authenticate(**authenticate_kwargs)

        if user is None:
            raise serializers.ValidationError('账号或密码错误')

        refresh = self.get_token(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }


# 地址 真实姓名的序列化器
class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'aname', 'aphone', 'addr', 'isdefault']
        read_only_fields = ['id']

    def create(self, validated_data):
        # 如果是默认地址，确保其他地址不是默认的
        if validated_data.get('isdefault'):
            Address.objects.filter(aUserInfo=validated_data['aUserInfo']).update(isdefault=False)
        return super().create(validated_data)


class RealNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealName
        fields = ['id', 'identity_card', 'realname', 'is_verified']
        read_only_fields = ['id']
