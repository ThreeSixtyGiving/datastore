# Generated by Django 2.2.13 on 2020-09-18 09:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("additional_data", "0006_tsgorgtype"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tsgorgtype",
            name="priority",
            field=models.IntegerField(
                help_text="Which pattern will take precedence (Higher number = higher priority)",
                unique=True,
            ),
        ),
    ]
