from rest_framework import serializers
from goodsapp.models import Category, Goods, GoodsDetail


# 类名获取序列化器
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'cname']


class GoodsDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsDetail
        fields = ['id', 'gdurl', 'is_main']


class GoodsListSerializer(serializers.ModelSerializer):
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Goods
        fields = ['id', 'gname', 'price', 'brand', 'is_hot', 'is_new', 'main_image']

    @staticmethod
    def get_main_image(obj):
        main_detail = obj.goodsdetail_set.filter(is_main=True).first()
        if main_detail:
            return main_detail.gdurl.url
        return None


class GoodsDetailPageSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    images = GoodsDetailSerializer(source='goodsdetail_set', many=True)

    class Meta:
        model = Goods
        fields = ['id', 'gname', 'gdesc', 'price', 'brand', 'stock', 'sales',
                  'is_hot', 'is_new', 'category', 'images', ]


class GoodsSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    brand = serializers.SerializerMethodField()

    class Meta:
        model = Goods
        fields = ['id', 'name', 'description', 'brand', 'price', 'stock',
                  'sales', 'is_hot', 'is_new', 'category', 'created_at']

    def get_gname(self, obj):
        lang = self.context.get('language', 'zh')
        return obj.get_name(lang)

    def get_gdesc(self, obj):
        lang = self.context.get('language', 'zh')
        return obj.get_description(lang)

    def get_brand(self, obj):
        lang = self.context.get('language', 'zh')
        return obj.get_brand(lang)

    def create(self, validated_data):
        # 处理多语言数据
        name_i18n = self.context.get('name_i18n', {})
        description_i18n = self.context.get('description_i18n', {})
        brand_i18n = self.context.get('brand_i18n', {})

        instance = super().create(validated_data)

        # 设置多语言字段
        if name_i18n:
            instance.set_i18n('name', name_i18n)
        if description_i18n:
            instance.set_i18n('description', description_i18n)
        if brand_i18n:
            instance.set_i18n('brand', brand_i18n)

        instance.save()
        return instance

    def update(self, instance, validated_data):
        # 处理多语言数据
        name_i18n = self.context.get('name_i18n', {})
        description_i18n = self.context.get('description_i18n', {})
        brand_i18n = self.context.get('brand_i18n', {})

        instance = super().update(instance, validated_data)

        # 更新多语言字段
        if name_i18n:
            instance.set_i18n('name', name_i18n)
        if description_i18n:
            instance.set_i18n('description', description_i18n)
        if brand_i18n:
            instance.set_i18n('brand', brand_i18n)

        instance.save()
        return instance
