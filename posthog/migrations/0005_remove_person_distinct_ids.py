# Generated by Django 2.2.7 on 2020-01-25 19:13

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("posthog", "0004_auto_20200125_0415"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="person",
            name="distinct_ids",
        ),
    ]
