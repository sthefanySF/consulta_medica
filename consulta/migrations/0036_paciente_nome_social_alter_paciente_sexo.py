# Generated by Django 5.0.1 on 2024-07-15 16:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('consulta', '0035_administrativo_nome_social_alter_administrativo_sexo'),
    ]

    operations = [
        migrations.AddField(
            model_name='paciente',
            name='nome_social',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Nome Social'),
        ),
        migrations.AlterField(
            model_name='paciente',
            name='sexo',
            field=models.CharField(choices=[('M', 'Masculino'), ('F', 'Feminino'), ('O', 'Outro')], max_length=1),
        ),
    ]
