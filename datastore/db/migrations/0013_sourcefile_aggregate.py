# Generated by Django 2.2.20 on 2021-05-27 10:27

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("db", "0012_sourcefile_grants"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourcefile",
            name="aggregate",
            field=django.contrib.postgres.fields.jsonb.JSONField(null=True),
        ),
    ]
