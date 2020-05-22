# Generated by Django 2.2.5 on 2019-12-02 16:35

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("db", "0008_remove_latest_total_grants"),
    ]

    operations = [
        migrations.AddField(
            model_name="grant",
            name="additional_data",
            field=django.contrib.postgres.fields.jsonb.JSONField(
                blank=True, null=True, verbose_name="Additional Grant data"
            ),
        ),
    ]