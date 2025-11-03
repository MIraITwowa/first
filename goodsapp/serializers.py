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
    name_i18n = serializers.JSONField(write_only=True, required=False)
    description_i18n = serializers.JSONField(write_only=True, required=False)
    brand_i18n = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = Goods
        fields = [
            'id',
            'gname',
            'gdesc',
            'brand',
            'price',
            'stock',
            'sales',
            'is_hot',
            'is_new',
            'category',
            'name_i18n',
            'description_i18n',
            'brand_i18n',
        ]
        extra_kwargs = {
            'gname': {'write_only': True},
            'gdesc': {'write_only': True},
        }

    def to_internal_value(self, data):
        mutable_data = data.copy() if hasattr(data, 'copy') else dict(data)
        if hasattr(mutable_data, '_mutable'):
            mutable_data._mutable = True
        if 'name' in mutable_data and 'gname' not in mutable_data:
            mutable_data['gname'] = mutable_data.get('name')
            try:
                del mutable_data['name']
            except Exception:
                mutable_data.pop('name', None)
        if 'description' in mutable_data and 'gdesc' not in mutable_data:
            mutable_data['gdesc'] = mutable_data.get('description')
            try:
                del mutable_data['description']
            except Exception:
                mutable_data.pop('description', None)
        return super().to_internal_value(mutable_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = self.context.get('language', 'zh')
        data['name'] = instance.get_gname(lang)
        data['description'] = instance.get_gdesc(lang)
        data['brand'] = instance.get_brand(lang)
        data.pop('gname', None)
        data.pop('gdesc', None)
        return data

    @staticmethod
    def _extract_i18n_fields(validated_data):
        payload = {}
        base_field_mapping = {
            'name': 'gname',
            'description': 'gdesc',
            'brand': 'brand',
        }
        for field in ('name', 'description', 'brand'):
            key = f'{field}_i18n'
            if key in validated_data:
                values = validated_data.pop(key)
                payload[field] = values
                if isinstance(values, dict):
                    default_value = values.get('zh')
                    if default_value is not None:
                        base_field = base_field_mapping[field]
                        validated_data.setdefault(base_field, default_value)
        return payload

    def _update_i18n_fields(self, instance, payload):
        updated_fields = set()
        for field, values in payload.items():
            if values is not None:
                updated_fields.update(instance.set_i18n(field, values))
        if updated_fields:
            instance.save(update_fields=list(updated_fields))
        return instance

    def create(self, validated_data):
        i18n_payload = self._extract_i18n_fields(validated_data)
        instance = super().create(validated_data)
        return self._update_i18n_fields(instance, i18n_payload)

    def update(self, instance, validated_data):
        i18n_payload = self._extract_i18n_fields(validated_data)
        instance = super().update(instance, validated_data)
        return self._update_i18n_fields(instance, i18n_payload)
