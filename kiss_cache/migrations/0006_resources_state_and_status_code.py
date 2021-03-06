# Generated by Django 2.2.3 on 2019-07-29 07:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("kiss_cache", "0005_resource_headers")]

    operations = [
        migrations.AddField(
            model_name="resource",
            name="status_code",
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="resource",
            name="state",
            field=models.IntegerField(
                choices=[(0, "Scheduled"), (1, "Downloading"), (2, "Finished")],
                default=0,
            ),
        ),
    ]
