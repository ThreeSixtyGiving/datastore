# Generated by Django 2.2.5 on 2019-11-21 14:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0006_auto_20191028_2225'),
    ]

    operations = [
        migrations.AddField(
            model_name='grant',
            name='latest',
            field=models.ManyToManyField(to='db.Latest'),
        ),
    ]