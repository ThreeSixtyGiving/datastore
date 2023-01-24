# Generated by Django 3.2.16 on 2023-01-24 13:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("additional_data", "0008_auto_20230123_1727"),
    ]

    operations = [
        migrations.CreateModel(
            name="CodelistCode",
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
                (
                    "list_name",
                    models.CharField(
                        help_text="The name of the CodeList the code belongs to",
                        max_length=200,
                    ),
                ),
                ("code", models.CharField(help_text="The code", max_length=200)),
                (
                    "title",
                    models.CharField(help_text="The title of the code", max_length=200),
                ),
                (
                    "description",
                    models.TextField(help_text="The long description of the code"),
                ),
            ],
            options={
                "unique_together": {("list_name", "code")},
            },
        ),
    ]
