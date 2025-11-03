import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from goodsapp.models import Category, Goods
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seed the database with sample data'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Create sample users
        self.stdout.write('Creating sample users...')
        users_data = [
            {
                'account': 'user1',
                'email': 'user1@example.com',
                'password': 'password123',
                'nickname': 'Alice',
                'phone': '13800138001'
            },
            {
                'account': 'user2', 
                'email': 'user2@example.com',
                'password': 'password123',
                'nickname': 'Bob',
                'phone': '13800138002'
            }
        ]
        
        for user_data in users_data:
            if not User.objects.filter(account=user_data['account']).exists():
                user = User.objects.create_user(
                    account=user_data['account'],
                    email=user_data['email'],
                    password=user_data['password'],
                    nickname=user_data['nickname'],
                    phone=user_data['phone']
                )
                self.stdout.write(f'Created user: {user.account}')
        
        # Create categories
        self.stdout.write('Creating categories...')
        categories_data = [
            {
                'name': 'Electronics',
                'description': 'Electronic devices and gadgets',
                'is_active': True
            },
            {
                'name': 'Clothing',
                'description': 'Fashion and apparel',
                'is_active': True
            },
            {
                'name': 'Books',
                'description': 'Books and educational materials',
                'is_active': True
            }
        ]
        
        created_categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            created_categories[category.name] = category
            if created:
                self.stdout.write(f'Created category: {category.name}')
        
        # Create goods
        self.stdout.write('Creating goods...')
        goods_data = [
            {
                'name': 'Smartphone',
                'description': 'Latest smartphone with amazing features',
                'price': Decimal('599.99'),
                'stock': 50,
                'category': created_categories['Electronics'],
                'is_active': True,
                'image': 'goods/phone.jpg'
            },
            {
                'name': 'Laptop',
                'description': 'High-performance laptop for work and gaming',
                'price': Decimal('1299.99'),
                'stock': 30,
                'category': created_categories['Electronics'],
                'is_active': True,
                'image': 'goods/laptop.jpg'
            },
            {
                'name': 'T-Shirt',
                'description': 'Comfortable cotton t-shirt',
                'price': Decimal('29.99'),
                'stock': 100,
                'category': created_categories['Clothing'],
                'is_active': True,
                'image': 'goods/tshirt.jpg'
            },
            {
                'name': 'Jeans',
                'description': 'Classic denim jeans',
                'price': Decimal('79.99'),
                'stock': 75,
                'category': created_categories['Clothing'],
                'is_active': True,
                'image': 'goods/jeans.jpg'
            },
            {
                'name': 'Python Programming Book',
                'description': 'Learn Python programming from scratch',
                'price': Decimal('39.99'),
                'stock': 200,
                'category': created_categories['Books'],
                'is_active': True,
                'image': 'goods/python_book.jpg'
            }
        ]
        
        for good_data in goods_data:
            goods, created = Goods.objects.get_or_create(
                name=good_data['name'],
                defaults=good_data
            )
            if created:
                self.stdout.write(f'Created goods: {goods.name}')
        
        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))