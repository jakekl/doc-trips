# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-04-17 16:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0006_auto_20170417_1218'),
    ]

    operations = [
        migrations.RenameField(
            model_name='attendee',
            old_name='sessions',
            new_name='registered_sessions'
        ),
        migrations.AlterField(
            model_name='attendee',
            name='registered_sessions',
            field=models.ManyToManyField(blank=True, related_name='registered', to='training.Session'),
        ),
    ]
