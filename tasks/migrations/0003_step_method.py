# Generated by Django 3.0.6 on 2020-05-18 20:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0002_auto_20200518_2005'),
    ]

    operations = [
        migrations.AddField(
            model_name='step',
            name='method',
            field=models.CharField(choices=[('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('PATCH', 'PATCH'), ('DELETE', 'DELETE'), ('HEAD', 'HEAD'), ('OPTIONS', 'OPTIONS')], default='POST', max_length=7),
        ),
    ]
