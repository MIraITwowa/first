# Generated manually to convert monetary fields to DecimalField.
from __future__ import annotations

import decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orderapp', '0002_order_order_num_alter_order_trade_no'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='total_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=decimal.Decimal('0.00'),
                max_digits=12,
                verbose_name='总金额',
            ),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='count',
            field=models.DecimalField(
                decimal_places=2,
                default=decimal.Decimal('0.00'),
                max_digits=12,
                verbose_name='价格',
            ),
        ),
    ]
