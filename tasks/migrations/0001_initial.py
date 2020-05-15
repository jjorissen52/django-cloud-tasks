# Generated by Django 3.0.6 on 2020-05-15 01:15

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Clock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of clock. Use something descriptive like "Every Day"', max_length=100)),
                ('gcp_name', models.TextField(help_text='Name of task in GCP with unaccepted characters removed.', null=True)),
                ('description', models.TextField(help_text='Description of what the Clock is for. Will be shown in Cloud Console.')),
                ('cron', models.CharField(help_text='Cron-style schedule, (test with https://crontab.guru/)', max_length=30)),
                ('management', models.CharField(choices=[('gcp', 'Cloud Scheduler'), ('manual', 'Manual')], default='gcp', help_text='Whether to automatically or manually control Clock in Cloud Scheduler', max_length=7)),
                ('status', models.CharField(choices=[('running', 'Running'), ('paused', 'Paused'), ('unknown', 'Unknown'), ('broken', 'Broken')], default='running', help_text='Status of the clock. ', max_length=8)),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of Task', max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='TaskSchedule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of Task Schedule', max_length=100, unique=True)),
                ('enabled', models.BooleanField(default=True, help_text='Whether or not task schedule is enabled.')),
                ('clock', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='tasks.Clock')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tasks.Task')),
            ],
        ),
        migrations.CreateModel(
            name='TaskExecution',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('started', 'Started'), ('success', 'Success'), ('failure', 'Failure')], default='started', max_length=7)),
                ('results', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tasks.Task')),
            ],
        ),
        migrations.CreateModel(
            name='Step',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of Step', max_length=100)),
                ('action', models.URLField(help_text='URL to place request')),
                ('payload', django.contrib.postgres.fields.jsonb.JSONField(blank=True, help_text='JSON Payload of request', null=True)),
                ('success_pattern', models.CharField(blank=True, help_text='Regex corresponding to successful execution', max_length=255, null=True)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tasks.Task')),
            ],
            options={
                'unique_together': {('name', 'task')},
            },
        ),
    ]
