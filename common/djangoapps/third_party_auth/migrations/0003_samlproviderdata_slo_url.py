# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('third_party_auth', '0002_auto_20160827_2046'),
    ]

    operations = [
        migrations.AddField(
            model_name='samlproviderdata',
            name='slo_url',
            field=models.URLField(null=True, verbose_name=b'SLO URL'),
        ),
    ]
