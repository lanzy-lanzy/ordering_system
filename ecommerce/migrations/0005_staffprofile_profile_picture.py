# Generated by Django 4.2.17 on 2025-03-30 09:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecommerce', '0004_staffprofile_staffactivity'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffprofile',
            name='profile_picture',
            field=models.ImageField(blank=True, null=True, upload_to='profile_pictures/'),
        ),
    ]
