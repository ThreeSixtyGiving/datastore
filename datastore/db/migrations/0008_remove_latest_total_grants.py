# Generated by Django 2.2.5 on 2019-11-21 15:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0007_grant_latest'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='latest',
            name='total_grants',
        ),
    ]