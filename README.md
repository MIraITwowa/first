# 跨境电商后端 API 服务（crossborder_trade）

一个基于 Django + Django REST Framework 的电商后端服务示例，涵盖用户认证、地址与实名信息、商品与分类、购物车、订单及模拟支付等核心模块，支持跨域访问与（可选）Redis 缓存。

- 框架与组件：Django 5、DRF、JWT（SimpleJWT）、django-cors-headers、django-redis
- 数据库：MySQL
- 缓存（可选）：Redis

## 功能模块

- 用户与认证
  - 账号注册/登录/退出（自定义用户模型，使用 account 作为登录字段）
  - JWT 鉴权（/api/token/、或在 /api/user/auth/ 的 login 流程中返回）
  - 地址管理（新增、修改、删除、列表）
  - 实名信息管理与状态查询
- 商品与分类
  - 分类列表、分类下商品列表、商品详情
  - 模型层已预置多语言字段（name/description/brand 的 i18n JSON 存储）
- 购物车
  - 添加、删除、更新数量、查看购物车详情
- 订单
  - 结算生成订单、订单列表与详情
- 支付
  - 模拟支付与回调（非真实三方支付，仅用于联调流程）
- 其他
  - CORS 跨域支持
  - 媒体资源托管（开发模式下 /media/）

## 目录结构（节选）

```
/home/engine/project
├── crossborder_trade/        # Django 项目配置（settings/urls 等）
├── userapp/                  # 用户、地址、实名信息模块
├── goodsapp/                 # 商品、分类、商品详情模块
├── cartapp/                  # 购物车模块
├── orderapp/                 # 订单模块
├── paymentapp/               # 支付（模拟）模块
├── templates/                # 示例数据（内含一份 JSON）
├── static/                   # 静态资源（如有）
├── media/                    # 媒体上传目录（DEBUG 下由 Django 提供）
├── manage.py
└── .gitignore
```

## 快速开始

### 1. 环境准备

- Python 3.10+
- MySQL 8.x（或兼容版本）
- Redis（可选，如果使用缓存）

建议安装以下依赖（可按需调整版本）：

```
pip install \
  django==5.1.5 \
  djangorestframework==3.15.2 \
  djangorestframework-simplejwt==5.3.1 \
  django-cors-headers==4.4.0 \
  django-redis==5.4.0 \
  mysqlclient==2.2.4
```

如本机编译 mysqlclient 困难，可改用 PyMySQL，并在 settings 中进行相应调整。

### 2. 数据库与配置

项目默认使用 MySQL，连接信息位于 `crossborder_trade/settings.py`：

```
DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'crossborder_trade',
    'USER': 'root',
    'PASSWORD': '2642',
    'HOST': '127.0.0.1',
    'PORT': '3306',
  }
}
```

建议通过 `crossborder_trade/local_settings.py` 覆盖敏感或本地配置（已在 settings 中自动尝试导入）：

```
# crossborder_trade/local_settings.py（示例）
SECRET_KEY = 'your-prod-like-secret'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'crossborder_trade',
    'USER': 'root',
    'PASSWORD': 'your_password',
    'HOST': '127.0.0.1',
    'PORT': '3306',
    'OPTIONS': {'charset': 'utf8mb4'},
  }
}

# 可选：Redis 缓存
CACHES = {
  'default': {
    'BACKEND': 'django_redis.cache.RedisCache',
    'LOCATION': 'redis://127.0.0.1:6379/1',
    'OPTIONS': { 'CLIENT_CLASS': 'django_redis.client.DefaultClient' },
  }
}
```

### 3. 初始化数据库

```
python manage.py makemigrations
python manage.py migrate
```

创建超级用户（自定义用户模型，登录字段为 account）：

```
python manage.py createsuperuser
# 按提示输入 account、password、username 等
```

### 4. 启动服务

```
python manage.py runserver 0.0.0.0:8000
```

在 DEBUG 模式下，媒体文件通过 `/media/` 提供访问。

## 接口速览与示例

以下仅列出主要接口，更多细节请参考各 app 的 urls 与 views。

- JWT 获取 Token（使用自定义账号字段 account）：
  - POST `/api/token/`
    - body: `{ "account": "alice", "password": "your_password" }`
    - 返回：`access`、`refresh`

- 用户注册/登录/退出：
  - POST `/api/user/auth/` 注册：
    - body: `{ "action": "register", "username": "Alice", "account": "alice", "password": "pwd" }`
  - POST `/api/user/auth/` 登录：
    - body: `{ "action": "login", "account": "alice", "password": "pwd" }`
    - 返回：`access`、`refresh`、`userId`
  - POST `/api/user/logout/`

- 地址管理（需 Authorization: Bearer <access>）：
  - GET/POST `/api/user/addresses/`
  - PUT/DELETE `/api/user/addresses/{id}/`

- 实名信息（需授权）：
  - GET/POST `/api/user/realname/`
  - GET `/api/user/verification/status/`

- 商品与分类（公开）：
  - GET `/api/trade/categories/` 分类列表
  - GET `/api/trade/category/{cid}/` 指定分类下商品
  - GET `/api/trade/goods/{goods_id}/` 商品详情

- 购物车（需授权）：
  - POST `/api/cart/add/{goods_id}/`，body: `{ "num": 2 }`
  - GET `/api/cart/detail/`
  - POST `/api/cart/update/{item_id}/`，body: `{ "num": 3 }`
  - POST `/api/cart/remove/{item_id}/`

- 订单（需授权）：
  - POST `/api/order/checkout/`，body: `{ "address_id": 1 }`（需先通过实名校验）
  - GET `/api/order/orders/` 列表
  - GET `/api/order/orders/{order_id}/` 详情

- 模拟支付（演示用）：
  - POST `/api/payment/mock-pay/`，body: `{ "order_id": 1, "total_amount": "99.99" }`
  - POST `/api/payment/mock-notify/`，body: `{ "payment_id": 1 }`

提示：默认模拟支付成功率由 `MOCK_PAYMENT_SUCCESS_RATE`（settings.py）控制。

## 认证与权限

- 大部分读写接口需要在 Header 中携带：`Authorization: Bearer <access_token>`。
- 商品与分类相关的 GET 接口默认开放访问。

## 其他说明

- CORS 已开启，默认允许所有来源（开发模式）。
- 媒体文件目录为 `media/`，开发模式下由 Django 通过 `/media/` 提供。
- 建议通过 `local_settings.py` 管理本地配置与敏感信息。

## 许可

该项目用于教学/演示目的，未附带开源协议。如需在生产环境使用，请完善安全、审计、支付对接、日志、监控、国际化等配套能力。
