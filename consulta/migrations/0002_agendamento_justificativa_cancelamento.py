# Generated by Django 4.2.7 on 2024-01-05 11:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('consulta', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='agendamento',
            name='justificativa_cancelamento',
            field=models.TextField(blank=True, null=True),
        ),
    ]
