from django.db import models
from django.contrib.auth.hashers import make_password

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, account, password=None, **extra_fields):
        if not account:
            raise ValueError('必须提供账号')
        # 标准化账号（如去除空格）
        account = self.normalize_email(account) if '@' in account else account
        user = self.model(account=account, **extra_fields)
        user.set_password(password)  # 自动处理密码哈希
        user.save(using=self._db)
        return user  # 必须返回用户对象

    def create_superuser(self, account, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(account, password, **extra_fields)


class UserInfo(AbstractBaseUser, PermissionsMixin):
    """用户表，名为UserInfo，继承自 AbstractBaseUser 以支持认证"""
    username = models.CharField(verbose_name="用户名", max_length=20)
    account = models.CharField(verbose_name="账号", max_length=64, unique=True)
    password = models.CharField(verbose_name="密码", max_length=225)  # 实际由父类处理
    create_time = models.DateTimeField(verbose_name="注册时间", auto_now_add=True)

    # 指定 account 为登录字段（替换默认的 username）
    USERNAME_FIELD = 'account'
    REQUIRED_FIELDS = ['username']  # 创建超级用户时需要填写的字段,不知道是不是要写“username”

    # 必须添加的字段（用于Admin后台）
    is_staff = models.BooleanField(default=False)  # 控制是否能访问Admin
    is_active = models.BooleanField(default=True)  # 是否激活账户
    objects = UserManager()  # 使用自定义的用户管理器

    def __str__(self):
        return self.username

    # 以下方法为 AbstractBaseUser 要求实现（根据需要调整）
    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    # 以后可能会用到
    # class Mate:
    #     ordering = ('id',)


class Address(models.Model):
    """地址表，名为Address"""
    aname = models.CharField(verbose_name="姓名", max_length=30)
    aphone = models.CharField(verbose_name="手机号", max_length=11)
    addr = models.CharField(verbose_name="地址", max_length=100)
    isdefault = models.BooleanField(default=False)  # 这是什么？
    aUserInfo = models.ForeignKey(UserInfo, on_delete=models.CASCADE)

    def __unicode__(self):
        return u'<Address:%s>' % self.aname


class RealName(models.Model):
    """实名检验，名为RealName"""
    identity_card = models.CharField(max_length=64, verbose_name="身份证号码")
    realname = models.CharField(verbose_name="实名", max_length=30)
    is_verified = models.BooleanField(default=True)
    rUserInfo = models.ForeignKey(UserInfo, on_delete=models.CASCADE)

    def __str__(self):
        return self.realname
