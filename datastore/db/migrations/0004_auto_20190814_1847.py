# Generated by Django 2.2 on 2019-08-14 18:47

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0003_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='status',
            name='when',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='status',
            name='status',
            field=models.CharField(default='idle', max_length=200),
        ),
    ]
