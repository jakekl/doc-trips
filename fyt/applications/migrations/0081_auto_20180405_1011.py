# Generated by Django 2.0.3 on 2018-04-05 14:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0080_auto_20180404_1737'),
    ]

    operations = [
        migrations.AlterField(
            model_name='volunteer',
            name='deadline_extension',
            field=models.DateTimeField(blank=True, default=None, help_text='Extension to the application deadline', null=True),
        ),
    ]
