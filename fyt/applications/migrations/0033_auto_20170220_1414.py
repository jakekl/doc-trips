# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-20 19:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0032_auto_20170220_1412'),
    ]

    operations = [
        migrations.AlterField(
            model_name='generalapplication',
            name='tshirt_size',
            field=models.CharField(choices=[('XS', 'Extra Small'), ('S', 'Small'), ('M', 'Medium'), ('L', 'Large'), ('XL', 'Extra Large'), ('XXL', 'Extra Extra Large')], max_length=2),
        ),
    ]
