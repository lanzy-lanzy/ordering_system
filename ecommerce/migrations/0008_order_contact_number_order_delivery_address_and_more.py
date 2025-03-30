# Generated by Django 5.1.1 on 2025-03-30 13:04

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecommerce', '0007_alter_staffprofile_role'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='contact_number',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_address',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='order',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='order',
            name='order_type',
            field=models.CharField(choices=[('DELIVERY', 'Delivery'), ('PICKUP', 'Pickup'), ('DINE_IN', 'Dine In')], default='DELIVERY', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(choices=[('CASH', 'Cash on Delivery'), ('CARD', 'Credit/Debit Card'), ('GCASH', 'GCash'), ('ONLINE', 'Other Online Payment')], default='CASH', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('PAID', 'Paid'), ('FAILED', 'Failed'), ('REFUNDED', 'Refunded')], default='PENDING', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='tax_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_method', models.CharField(choices=[('CASH', 'Cash on Delivery'), ('CARD', 'Credit/Debit Card'), ('GCASH', 'GCash'), ('ONLINE', 'Other Online Payment')], max_length=20)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed'), ('REFUNDED', 'Refunded')], default='PENDING', max_length=20)),
                ('reference_number', models.CharField(blank=True, max_length=100, null=True)),
                ('payment_proof', models.ImageField(blank=True, null=True, upload_to='payment_proofs/')),
                ('payment_date', models.DateTimeField(auto_now_add=True)),
                ('verification_date', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='ecommerce.order')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-payment_date'],
            },
        ),
    ]
