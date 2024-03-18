# Generated by Django 3.2.16 on 2024-03-18 19:52

import django.contrib.postgres.indexes
import django.contrib.postgres.operations
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("db", "0022_auto_20240227_1648"),
    ]

    operations = [
        django.contrib.postgres.operations.BtreeGinExtension(),
        migrations.AddIndex(
            model_name="grant",
            index=django.contrib.postgres.indexes.BTreeIndex(
                fields=["publisher_org_id"], name="db_grant_publish_53bcd4_btree"
            ),
        ),
        migrations.AddIndex(
            model_name="grant",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["recipient_org_ids"], name="db_grant_recipie_a7115b_gin"
            ),
        ),
        migrations.AddIndex(
            model_name="grant",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["source_file", "recipient_org_ids"],
                name="db_grant_source__83fe64_gin",
            ),
        ),
        migrations.AddIndex(
            model_name="grant",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["funding_org_ids"], name="db_grant_funding_52835f_gin"
            ),
        ),
        migrations.AddIndex(
            model_name="grant",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["source_file", "funding_org_ids"],
                name="db_grant_source__3f2a23_gin",
            ),
        ),
    ]
