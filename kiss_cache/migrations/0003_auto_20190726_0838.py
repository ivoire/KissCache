# Generated by Django 2.2.3 on 2019-07-26 08:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("kiss_cache", "0002_alter_resources")]

    operations = [
        migrations.AlterField(
            model_name="resource",
            name="state",
            field=models.IntegerField(
                choices=[
                    (0, "Scheduled"),
                    (1, "Downloading"),
                    (2, "Completed"),
                    (3, "Failed"),
                ],
                default=0,
            ),
        ),
        migrations.AlterField(
            model_name="resource", name="ttl", field=models.IntegerField(default=86400)
        ),
    ]