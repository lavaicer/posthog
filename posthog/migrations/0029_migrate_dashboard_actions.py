# Generated by Django 3.0.3 on 2020-03-05 17:05

from django.db import migrations


def migrate_to_dict(apps, schema_editor):
    DashboardItem = apps.get_model("posthog", "DashboardItem")
    for item in DashboardItem.objects.filter(filters__actions__isnull=False):
        item.filters["actions"] = [{"id": id} for id in item.filters["actions"]]
        item.save()


def migrate_to_array(apps, schema_editor):
    DashboardItem = apps.get_model("posthog", "DashboardItem")
    for item in DashboardItem.objects.filter(filters__actions__isnull=False):
        item.filters["actions"] = [id["id"] for id in item.filters["actions"]]
        item.save()


class Migration(migrations.Migration):

    dependencies = [
        ("posthog", "0028_actionstep_url_matching"),
    ]

    operations = [migrations.RunPython(migrate_to_dict, migrate_to_array, elidable=True)]
