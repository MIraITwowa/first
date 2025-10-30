from django.test import TestCase

from cartapp.models import CartItem
from userapp.models import UserInfo


class CartSignalTests(TestCase):
    def test_new_user_has_no_cart_items_by_default(self):
        user = UserInfo.objects.create_user(
            account='empty@example.com',
            password='pass1234',
            username='empty',
        )
        self.assertFalse(CartItem.objects.filter(userInfo=user).exists())
