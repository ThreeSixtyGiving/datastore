# Generated by Django 2.2 on 2019-07-26 15:19

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GetterRun",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("datetime", models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name="Publisher",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("data", django.contrib.postgres.fields.jsonb.JSONField()),
                ("name", models.TextField(blank=True, null=True)),
                (
                    "getter_run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="db.GetterRun"
                    ),
                ),
                ("prefix", models.CharField(default=0, max_length=300)),
            ],
            options={
                "unique_together": {("getter_run", "prefix")},
            },
        ),
        migrations.CreateModel(
            name="SourceFile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("data", django.contrib.postgres.fields.jsonb.JSONField()),
                (
                    "datagetter_data",
                    django.contrib.postgres.fields.jsonb.JSONField(null=True),
                ),
                ("data_valid", models.BooleanField(default=False)),
                ("acceptable_license", models.BooleanField(default=False)),
                (
                    "getter_run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="db.GetterRun"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Grant",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("grant_id", models.CharField(max_length=300)),
                (
                    "data",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        verbose_name="Grant data"
                    ),
                ),
                (
                    "source_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="db.SourceFile",
                    ),
                ),
                (
                    "getter_run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="db.GetterRun"
                    ),
                ),
                (
                    "publisher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="db.Publisher",
                    ),
                ),
            ],
        ),
    ]
