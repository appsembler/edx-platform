# -*- coding: utf-8 -*-


from django.db import migrations, models
import jsonfield.fields
import openedx.core.djangoapps.appsembler.sites.utils


class Migration(migrations.Migration):

    dependencies = [
        ('site_configuration', '0002_auto_20160720_0231'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='page_elements',
            field=jsonfield.fields.JSONField(default=openedx.core.djangoapps.appsembler.sites.utils.get_initial_page_elements, blank=True),
        ),
        migrations.AddField(
            model_name='siteconfiguration',
            name='sass_variables',
            field=models.TextField(default=openedx.core.djangoapps.appsembler.sites.utils.get_initial_sass_variables, blank=True),
        ),
    ]
