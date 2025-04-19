from django.db import models
from django.db.models import JSONField


# import collections


# Create your models here.
class Category(models.Model):
    cname = models.CharField(max_length=50, verbose_name="商品类别名")

    def __str__(self):
        return u'<Category %s>' % self.cname


class Goods(models.Model):
    gname = models.CharField(max_length=100, unique=True, verbose_name="商品名")
    gdesc = models.TextField(max_length=100, verbose_name="商品描述")
    price = models.DecimalField(max_digits=7, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='goods_set')
    brand = models.CharField(max_length=100)  # 品牌名称
    stock = models.IntegerField(default=0)  # 库存
    sales = models.IntegerField(default=0)  # 销量
    is_hot = models.BooleanField(default=False)  # 是否热门
    is_new = models.BooleanField(default=False)  # 是否新品
    # 多语言字段
    name_i18n = JSONField(default=dict)  # {'zh': '商品名称', 'en': 'Product Name'}
    description_i18n = JSONField(default=dict)
    brand_i18n = JSONField(default=dict)

    def __str__(self):
        return f'<Goods %s>' % self.gname

    def get_gname(self, lang='zh'):
        """获取指定语言的商品名称"""
        return self.name_i18n.get(lang, self.name_i18n.get('zh', self.gname))

    def get_gdesc(self, lang='zh'):
        """获取指定语言的商品描述"""
        return self.description_i18n.get(lang, self.description_i18n.get('zh', self.gdesc))

    def get_brand(self, lang='zh'):
        """获取指定语言的品牌名称"""
        return self.brand_i18n.get(lang, self.brand_i18n.get('zh', self.brand))

    def set_i18n(self, field, values):
        """设置多语言字段的值
        :param field: 字段名称（name/description/brand）
        :param values: 字典格式的多语言值 {'zh': '值', 'en': 'value'}
        """
        setattr(self, f'{field}_i18n', values)
        # 设置默认语言（中文）作为兼容性字段的值
        setattr(self, field, values.get('zh', ''))


class GoodsDetailName(models.Model):
    gdname = models.CharField(max_length=100, verbose_name="商品详情页中的信息类名")  # 可重复

    def __str__(self):
        return self.gdname


class GoodsDetail(models.Model):
    gdurl = models.ImageField(upload_to='', verbose_name='图片地址')  # 默认media路径，已配置
    goodsdname = models.ForeignKey(GoodsDetailName, on_delete=models.CASCADE)
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, related_name='goodsdetail_set')
    is_main = models.BooleanField(default=False)  # 是否主图

    def __str__(self):
        return f'{self.goods.gname} - {self.goodsdname.gdname}'
