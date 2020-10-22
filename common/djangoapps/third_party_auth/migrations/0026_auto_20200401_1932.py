# Generated by Django 2.0.13 on 2020-04-01 19:32

from django.db import migrations, models
import django.db.models.deletion
import third_party_auth.models


class Migration(migrations.Migration):

    dependencies = [
        ('third_party_auth', '0025_auto_20200303_1448'),
    ]

    operations = [
        migrations.AlterField(
            model_name='samlproviderconfig',
            name='saml_configuration',
            field=models.ForeignKey(blank=True, limit_choices_to=third_party_auth.models.active_saml_configurations_filter, null=True, on_delete=django.db.models.deletion.SET_NULL, to='third_party_auth.SAMLConfiguration'),
        ),
    ]
