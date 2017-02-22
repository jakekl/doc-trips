# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-22 22:42
from __future__ import unicode_literals

from django.db import migrations, models

"""
Migrate the `leadership_style` question, which was used in 2016, to a
dynamic question.

Also fixes the Question.index unique constraint so that it is only unique by
trips_year.
"""

YEAR = 2016


def migrate_leadership_style(apps, schema_editor):

    Question = apps.get_model('applications', 'Question')
    Answer = apps.get_model('applications', 'Answer')
    GeneralApplication = apps.get_model('applications', 'GeneralApplication')

    text = (
        'Describe your leadership style and your role in a group. Please go to '
        '<a href="https://sites.google.com/a/stgregoryschool.org/mr-roberts/home/theoretical-and-applied-leadership/leadership-squares">this website</a> '
        'and use the four descriptions (Puzzle Master, Director, Coach, or '
        'Diplomat) as a framework for your answer. Please order the four '
        'leadership styles in order of how much you identify with each one of '
        'them, and use them as a launching pad to discuss your strengths and '
        'weaknesses. This is not supposed to box you in to a specific '
        'category, but rather it serves to provide you with a structure to '
        'discuss your strengths and weaknesses and group-work styles so that '
        'we can effectively pair you with a co-leader or fellow croolings who '
        'complements you. Each leadership style is equally valuable, and we '
        'will use answers to this question to balance our teams as a whole.')

    question = Question.objects.create(
        trips_year_id=YEAR,
        question=text,
        type='ALL',
        index=0
    )

    for app in GeneralApplication.objects.filter(trips_year=YEAR):
        answer = app.leadership_style.strip() or "NO ANSWER"
        print(answer)

        Answer.objects.create(
            application=app,
            question=question,
            answer=answer
        )


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0001_initial'),
        ('applications', '0056_auto_20170221_1734'),
    ]

    operations = [
        # Fix Question unique constraint
        migrations.AlterField(
            model_name='question',
            name='index',
            field=models.PositiveIntegerField(help_text='change this value to re-order the questions', verbose_name='order'),
        ),
        migrations.AlterUniqueTogether(
            name='question',
            unique_together=set([('index', 'trips_year')]),
        ),
        migrations.RunPython(migrate_leadership_style)
    ]
