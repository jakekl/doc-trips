# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-22 23:06
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0057_auto_20170222_1742'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='generalapplication',
            name='leadership_style',
        ),
    ]
