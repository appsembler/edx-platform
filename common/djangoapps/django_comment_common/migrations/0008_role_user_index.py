# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('django_comment_common', '0007_discussionsidmapping'),
    ]

    operations = [
        migrations.RunSQL(
            'CREATE INDEX dcc_role_users_user_role_idx ON django_comment_client_role_users(user_id, role_id);'
        ),
    ]
