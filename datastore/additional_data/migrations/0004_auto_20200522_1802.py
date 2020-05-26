# Generated by Django 2.2.10 on 2020-05-22 18:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("additional_data", "0003_geolookup"),
    ]

    operations = [
        migrations.AlterField(
            model_name="geolookup",
            name="areacode",
            field=models.CharField(db_index=True, max_length=200, unique=True),
        ),
        migrations.AlterField(
            model_name="geolookup",
            name="areatype",
            field=models.CharField(
                choices=[
                    ("lsoa", "Lower Super Output Area"),
                    ("msoa", "Middle Super Output Area"),
                    ("la", "Local Authority"),
                    ("ward", "Ward"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
    ]
