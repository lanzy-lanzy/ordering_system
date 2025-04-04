# Generated by Django 4.2.17 on 2025-04-04 04:40

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ecommerce', '0020_reservation_is_processed_reservation_processed_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='payment_status',
            field=models.CharField(choices=[('UNPAID', 'Unpaid'), ('PARTIALLY_PAID', 'Partially Paid'), ('PAID', 'Paid'), ('REFUNDED', 'Refunded')], default='UNPAID', max_length=15),
        ),
        migrations.AddField(
            model_name='reservation',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.CreateModel(
            name='ReservationPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_type', models.CharField(choices=[('FULL', 'Full Payment'), ('DEPOSIT', 'Deposit (50%)')], default='DEPOSIT', max_length=10)),
                ('payment_method', models.CharField(choices=[('CASH', 'Cash'), ('CASH_ON_HAND', 'Cash on Hand'), ('CARD', 'Credit/Debit Card'), ('GCASH', 'GCash'), ('ONLINE', 'Other Online Payment')], default='GCASH', max_length=20)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed'), ('REFUNDED', 'Refunded')], default='PENDING', max_length=20)),
                ('reference_number', models.CharField(blank=True, max_length=100, null=True)),
                ('payment_proof', models.ImageField(blank=True, null=True, upload_to='reservation_payment_proofs/')),
                ('payment_date', models.DateTimeField(auto_now_add=True)),
                ('verification_date', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('reservation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='ecommerce.reservation')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_reservation_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-payment_date'],
            },
        ),
    ]
