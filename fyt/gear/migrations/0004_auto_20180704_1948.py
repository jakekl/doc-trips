# Generated by Django 2.0.6 on 2018-07-04 23:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gear', '0003_auto_20180701_1253'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gearrequest',
            name='incoming_student',
            field=models.OneToOneField(editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='gear_request', to='incoming.IncomingStudent'),
        ),
        migrations.AlterField(
            model_name='gearrequest',
            name='volunteer',
            field=models.OneToOneField(editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='gear_request', to='applications.Volunteer'),
        ),
    ]