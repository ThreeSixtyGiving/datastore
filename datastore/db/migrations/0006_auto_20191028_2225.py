# Generated by Django 2.2.5 on 2019-10-28 22:25

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0005_auto_20190816_1015'),
    ]

    operations = [
        migrations.CreateModel(
            name='Latest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('series', models.TextField(choices=[('NEXT', 'Next'), ('CURRENT', 'Current'), ('PREVIOUS', 'Previous')])),
                ('updated', models.DateTimeField(default=django.utils.timezone.now)),
                ('total_grants', models.IntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name='sourcefile',
            name='latest',
            field=models.ManyToManyField(to='db.Latest'),
        ),
    ]