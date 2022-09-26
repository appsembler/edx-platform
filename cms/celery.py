"""
Import celery, load its settings from the django settings
and auto discover tasks in all installed django apps.

Taken from: https://celery.readthedocs.org/en/latest/django/first-steps-with-django.html
"""


import beeline
import logging
import os

# Patch the xml libs before anything else.
from safe_lxml import defuse_xml_libs

defuse_xml_libs()


# Set the default Django settings module for the 'celery' program
# and then instantiate the Celery singleton.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cms.envs.production')
from openedx.core.lib.celery import APP  # pylint: disable=wrong-import-position,unused-import

from celery.signals import worker_process_init, task_prerun, task_postrun
from django.conf import settings


# honeycomb setup
@worker_process_init.connect
def initialize_honeycomb(**kwargs):
    if settings.HONEYCOMB_WRITEKEY and settings.HONEYCOMB_DATASET:
        logging.info('beeline initialization in process pid {}'.format(os.getpid()))
        beeline.init(
            writekey=settings.HONEYCOMB_WRITEKEY,
            dataset=settings.HONEYCOMB_DATASET,
            service_name='cms-celery'
        )


@task_prerun.connect
def start_celery_trace(task_id, task, args, kwargs, **rest_args):
    queue_name = task.request.delivery_info.get("exchange", None)
    task.request.trace = beeline.start_trace(
        context={
            "name": "celery",
            "celery.task_id": task_id,
            "celery.args": args,
            "celery.kwargs": kwargs,
            "celery.task_name": task.name,
            "celery.queue": queue_name,
        }
    )


# optional: finish and send the trace at the end of each task
@task_postrun.connect
def end_celery_trace(task, state, **kwargs):
    beeline.add_field("celery.status", state)
    beeline.finish_trace(task.request.trace)

