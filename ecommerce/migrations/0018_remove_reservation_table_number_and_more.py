# Generated by Django 4.2.17 on 2025-04-03 14:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ecommerce', '0017_reservation_table_number'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reservation',
            name='table_number',
        ),
        migrations.AddField(
            model_name='order',
            name='cancellation_notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='cancellation_reason',
            field=models.CharField(blank=True, choices=[('CUSTOMER_REQUEST', 'Customer Request'), ('PAYMENT_ISSUE', 'Payment Issue'), ('OUT_OF_STOCK', 'Items Out of Stock'), ('STORE_CLOSED', 'Store Closed'), ('DUPLICATE_ORDER', 'Duplicate Order'), ('OTHER', 'Other Reason')], max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='cancelled_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cancelled_orders', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='Refund',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('reason', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSED', 'Processed'), ('REJECTED', 'Rejected')], default='PENDING', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('initiated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='initiated_refunds', to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='refunds', to='ecommerce.order')),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_refunds', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
