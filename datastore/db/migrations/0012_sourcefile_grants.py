# Generated by Django 2.2.20 on 2021-05-25 16:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0011_auto_20210525_1336'),
    ]

    operations = [
        migrations.AddField(
            model_name='sourcefile',
            name='grants',
            field=models.IntegerField(default=0),
        ),
    ]
