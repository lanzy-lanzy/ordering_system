# Generated by Django 4.2.17 on 2025-04-04 04:00

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ecommerce', '0019_reservation_table_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='is_processed',
            field=models.BooleanField(default=False, help_text='Whether the reservation has been processed by a cashier'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='processed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='processed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_reservations', to=settings.AUTH_USER_MODEL),
        ),
    ]
