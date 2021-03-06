# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-20 21:45
from __future__ import unicode_literals

from django.db import migrations, models
import fyt.applications.models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0046_auto_20170220_1638'),
    ]

    operations = [
        migrations.AlterField(
            model_name='generalapplication',
            name='in_goodstanding_with_college',
            field=models.BooleanField(default=False, validators=[fyt.applications.models.validate_condition_true], verbose_name='By applying to volunteer for Trips, I acknowledge that I am in good standing with the College. This will be verified by DOC Trips through the Undergraduate Dean’s Office.'),
        ),
    ]
