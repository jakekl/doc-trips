# Generated by Django 2.0.4 on 2018-04-05 22:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0097_auto_20180405_1847'),
    ]

    operations = [
        migrations.AlterField(
            model_name='score',
            name='comments',
            field=models.ManyToManyField(through='applications.AnswerComment', to='applications.ScoreQuestion'),
        ),
    ]
