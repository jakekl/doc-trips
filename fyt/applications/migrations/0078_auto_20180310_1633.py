# Generated by Django 2.0.2 on 2018-03-10 21:33

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),
        ('applications', '0077_auto_20180304_1233'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='volunteer',
            unique_together={('trips_year', 'applicant')},
        ),
    ]
