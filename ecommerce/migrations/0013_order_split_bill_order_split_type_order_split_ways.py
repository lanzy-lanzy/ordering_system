# Generated by Django 4.2.17 on 2025-04-03 07:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecommerce', '0012_order_created_by_order_customer_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='split_bill',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='order',
            name='split_type',
            field=models.CharField(choices=[('EQUAL', 'Equal Split'), ('CUSTOM', 'Custom Split')], default='EQUAL', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='split_ways',
            field=models.PositiveIntegerField(default=2),
        ),
    ]
