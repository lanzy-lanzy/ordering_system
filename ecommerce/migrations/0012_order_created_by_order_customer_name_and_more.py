# Generated by Django 4.2.17 on 2025-04-03 07:08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ecommerce', '0011_order_cancelled_at_order_completed_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_orders', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='order',
            name='customer_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='order',
            name='customer_phone',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='estimated_dining_time',
            field=models.PositiveIntegerField(default=60, help_text='Estimated dining time in minutes'),
        ),
        migrations.AddField(
            model_name='order',
            name='number_of_guests',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='order',
            name='server_assigned',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='served_orders', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='order',
            name='table_number',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
