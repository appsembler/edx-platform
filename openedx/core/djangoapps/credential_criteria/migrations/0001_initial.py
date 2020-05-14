# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2020-05-14 02:56
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import opaque_keys.edx.django.models
import openedx.core.djangoapps.credential_criteria.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CredentialCriteria',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('is_active', models.BooleanField()),
                ('credential_id', models.PositiveIntegerField()),
                ('credential_type', models.CharField(choices=[(b'badge', b'badge'), (b'coursecertificate', b'coursecertificate'), (b'programcertificate', b'programcertificate')], max_length=255)),
                ('_criteria_narrative', models.TextField()),
                ('_criteria_url', models.URLField()),
                ('_evidence_narrative', models.TextField()),
                ('_evidence_url', models.URLField()),
            ],
            options={
                'ordering': ('-modified', '-created'),
                'abstract': False,
                'get_latest_by': 'modified',
            },
        ),
        migrations.CreateModel(
            name='CredentialUsageKeyCriterion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('criterion_type', models.CharField(choices=[(set(['Completion', 'Credential', 'Enrollment', 'Pass/Fail', 'Letter Grade', 'Score']), set(['Completion', 'Credential', 'Enrollment', 'Pass/Fail', 'Letter Grade', 'Score']))], max_length=255)),
                ('satisfaction_threshold', models.FloatField()),
                ('block_id', opaque_keys.edx.django.models.UsageKeyField(max_length=255, validators=[openedx.core.djangoapps.credential_criteria.models.validate_usage_key])),
                ('criteria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='credential_criteria.CredentialCriteria')),
            ],
            options={
                'verbose_name': 'UsageKey Credential Criterion',
            },
        ),
        migrations.CreateModel(
            name='UserCredentialCriterion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('criterion_id', models.PositiveIntegerField()),
                ('satisfied', models.BooleanField()),
                ('criterion_content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='usercredentialcriterion',
            unique_together=set([('user', 'criterion_id')]),
        ),
    ]
