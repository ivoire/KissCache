# Generated by Django 2.2.11 on 2020-03-18 09:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("kiss_cache", "0009_statistic_value_biginteger")]

    operations = [migrations.RemoveField(model_name="resource", name="path")]
