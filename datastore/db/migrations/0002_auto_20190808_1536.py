# Generated by Django 2.2 on 2019-08-08 15:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourcefile",
            name="downloads",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="publisher",
            name="prefix",
            field=models.CharField(max_length=300),
        ),
    ]
