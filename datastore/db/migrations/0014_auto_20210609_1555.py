# Generated by Django 2.2.20 on 2021-06-09 15:55

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("db", "0013_sourcefile_aggregate"),
    ]

    operations = [
        migrations.AddField(
            model_name="publisher",
            name="aggregate",
            field=django.contrib.postgres.fields.jsonb.JSONField(null=True),
        ),
        migrations.AddField(
            model_name="publisher",
            name="quality",
            field=django.contrib.postgres.fields.jsonb.JSONField(null=True),
        ),
    ]
