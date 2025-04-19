from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import make_password, check_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserInfo
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

from rest_framework.permissions import IsAuthenticated
from .models import Address, RealName
from .serializers import AddressSerializer, RealNameSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@api_view(['POST'])
def auth(request):
    action = request.data.get('action')
    if action == 'register':
        username = request.data.get('username')
        account = request.data.get('account')
        password = request.data.get('password')

        if not all([username, account, password]):
            return Response({'error': 'Please provide username, account and password'},
                            status=status.HTTP_400_BAD_REQUEST)

        if UserInfo.objects.filter(account=account).exists():
            return Response({'error': 'Account is already taken'}, status=status.HTTP_400_BAD_REQUEST,
                            )

        hashed_password = make_password(password)
        UserInfo.objects.create(username=username, account=account, password=hashed_password)
        return Response({'message': 'User created successfully'}, status=status.HTTP_201_CREATED,
                        )

    elif action == 'login':
        account = request.data.get('account')
        password = request.data.get('password')

        try:
            user = UserInfo.objects.get(account=account)
            if check_password(password, user.password):
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'userId': str(user.id),
                })
            else:
                return Response({'error': 'wrong password'}, status=status.HTTP_401_UNAUTHORIZED,
                                )
        except UserInfo.DoesNotExist:
            return Response({'error': 'The account does not exist'}, status=status.HTTP_401_UNAUTHORIZED,
                            )

    else:
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST,
                        )


@api_view(['POST'])
def logout(request):
    try:
        # 获取当前用户的token
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]  # 去掉 'Bearer ' 前缀
            # 这里可以添加token到黑名单的逻辑，如果需要的话

        return Response({
            'message': '退出成功',
            'status': 'success'
        })
    except Exception as e:
        return Response({
            'error': '退出失败',
            'status': 'error'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def address_list(request):
    """
    获取用户的所有地址或创建新地址
    """
    if request.method == 'GET':
        addresses = Address.objects.filter(aUserInfo=request.user)
        serializer = AddressSerializer(addresses, many=True)
        return Response({'status': 'success', 'addresses': serializer.data})

    elif request.method == 'POST':
        # 如果设置为默认地址，先将其他地址的默认状态取消
        if request.data.get('isdefault', False):
            Address.objects.filter(aUserInfo=request.user).update(isdefault=False)

        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(aUserInfo=request.user)
            return Response({
                'status': 'success',
                'message': '地址添加成功',
                'address': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'status': 'error',
            'message': '数据验证失败',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def address_detail(request, pk):
    """
    修改或删除指定地址
    """
    try:
        address = Address.objects.get(pk=pk, aUserInfo=request.user)
    except Address.DoesNotExist:
        return Response({
            'status': 'error',
            'message': '地址不存在'
        }, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        # 如果设置为默认地址，先将其他地址的默认状态取消
        if request.data.get('isdefault', False):
            Address.objects.filter(aUserInfo=request.user).exclude(pk=pk).update(isdefault=False)

        serializer = AddressSerializer(address, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': '地址修改成功',
                'address': serializer.data
            })
        return Response({
            'status': 'error',
            'message': '数据验证失败',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        address.delete()
        return Response({
            'status': 'success',
            'message': '地址删除成功'
        })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def realname_view(request):
    """
    获取或提交实名认证信息
    """
    try:
        realname = RealName.objects.get(rUserInfo=request.user)
        if request.method == 'GET':
            serializer = RealNameSerializer(realname)
            return Response({
                'status': 'success',
                'realname': serializer.data
            })
        return Response({
            'status': 'error',
            'message': '您已完成实名认证，无法重复认证'
        }, status=status.HTTP_400_BAD_REQUEST)
    except RealName.DoesNotExist:
        if request.method == 'POST':
            serializer = RealNameSerializer(data=request.data)
            if serializer.is_valid():
                # serializer.save(rUserInfo=request.user)
                # 保存时设置 is_verified=True
                instance = serializer.save(
                    rUserInfo=request.user,
                    is_verified=True  # 明确设置验证状态
                )
                return Response({
                    'status': 'success',
                    'message': '实名认证提交成功',
                    'realname': serializer.data,
                    'is_verified': True
                }, status=status.HTTP_201_CREATED)
            return Response({
                'status': 'error',
                'message': '数据验证失败',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'status': 'success',
            'realname': None
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verification_status(request):
    """
    获取用户实名认证状态
    """
    try:
        # 获取用户的实名认证信息
        real_name = RealName.objects.filter(rUserInfo=request.user).first()
        is_verified = bool(real_name) and real_name.is_verified

        return Response({
            'status': 'success',
            'is_verified': real_name.is_verified if real_name else False
        })
    except Exception as e:
        # 添加详细的错误日志
        import traceback
        print(f"实名认证状态检查错误: {str(e)}")
        print(traceback.format_exc())  # 打印完整的错误堆栈
        return Response({
            'status': 'error',
            'message': '获取实名认证状态失败'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
