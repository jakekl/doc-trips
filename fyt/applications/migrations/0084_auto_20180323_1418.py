# Generated by Django 2.0.3 on 2018-03-23 18:18

from django.db import migrations

"""Move the single score into a split croo/leader score."""

def copy_scores(apps, schema_editor):

    Score = apps.get_model('applications', 'Score')
    for s in Score.objects.all():
        s.leader_score = s.score
        s.croo_score = s.score
        s.save()


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0083_auto_20180323_1417'),
    ]

    operations = [
        migrations.RunPython(copy_scores)
    ]
