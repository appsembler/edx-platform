# -*- coding: utf-8 -*-
from django.db import migrations, models


def remove_user_email_uniqueness_constraint(apps, schema_editor):
    # Do we already have an email uniqueness constraint?
    cursor = schema_editor.connection.cursor()
    constraints = schema_editor.connection.introspection.get_constraints(cursor, "auth_user")
    email_constraint = constraints.get("email", {})
    if email_constraint.get("columns") == ["email"] and email_constraint.get("unique") == True:
        # There is a constraint, let's remove it
        schema_editor.execute("alter table auth_user drop index email")


class Migration(migrations.Migration):

    dependencies = [
        ('appsembler_sites', '0001_initial'),
        ('database_fixups', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remove_user_email_uniqueness_constraint, atomic=False)
    ]
