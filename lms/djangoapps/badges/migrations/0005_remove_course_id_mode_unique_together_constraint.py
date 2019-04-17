# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('badges', '0004_update_slug_change_unique_together_constraint'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='badgeclass',
            unique_together=set([]),
        ),
    ]
