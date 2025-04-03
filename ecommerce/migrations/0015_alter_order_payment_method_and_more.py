# Generated by Django 5.1.4 on 2025-04-03 07:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecommerce', '0014_order_cash_on_hand_order_change_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='payment_method',
            field=models.CharField(choices=[('CASH', 'Cash'), ('CASH_ON_HAND', 'Cash on Hand'), ('CARD', 'Credit/Debit Card'), ('GCASH', 'GCash'), ('ONLINE', 'Other Online Payment')], default='CASH', max_length=20),
        ),
        migrations.AlterField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(choices=[('CASH', 'Cash'), ('CASH_ON_HAND', 'Cash on Hand'), ('CARD', 'Credit/Debit Card'), ('GCASH', 'GCash'), ('ONLINE', 'Other Online Payment')], max_length=20),
        ),
    ]
