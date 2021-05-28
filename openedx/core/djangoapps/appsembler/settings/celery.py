"""
Import celery, load its settings from the django settings
and auto discover tasks in all installed django apps.

Taken from: https://celery.readthedocs.org/en/latest/django/first-steps-with-django.html
"""


import logging
import os

from celery import Celery
from celery.signals import worker_process_init, task_prerun, task_postrun
from django.conf import settings

from openedx.core.lib.celery.routers import AlternateEnvironmentRouter
from lms.celery import Router

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proj.settings')

APP = Celery('proj')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
APP.config_from_object('django.conf:settings')
APP.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


class TahoeRouter(AlternateEnvironmentRouter): # consider using AlternateEnvironmentRouter instead
    """
    An implementation of LMS Router, for routing Tahoe specific tasks.
    """

    @property
    def alternate_env_tasks(self):
        """
        Defines alternate environment tasks, as a dict of form { task_name: alternate_queue }
        """
        # ENABLE_DAILY_METRICS_IMPORT
        # ENABLE_DAILY_MAU_IMPORT
        # ENABLE_FIGURES_MONTHLY_METRICS

        # FIGURES_MONTHLY_METRICS_ROUTING_KEY = "edx.lms.core.high"
        # POPULATE_ALL_MAU_ROUTING_KEY
        # POPULATE_DAILY_METRICS_ROUTING_KEY
        
        return {
            #'figures.tasks.run_figures_monthly_metrics': settings.FIGURES_MONTHLY_METRICS_ROUTING_KEY,
            'figures.tasks.run_figures_monthly_metrics': 'edx.lms.core.high_mem',
        }
    
    @property
    def explicit_queues(self):
        """
        Defines specific queues for tasks to run in (typically outside of the cms environment),
        as a dict of form { task_name: queue_name }.
        """
        return {
            'figures.tasks.run_figures_monthly_metrics': 'edx.lms.core.high_mem',
            'figures.tasks.populate_daily_metrics': 'edx.lms.core.high_mem',
            'figures.tasks.populate_all_mau': 'edx.lms.core.high_mem',
            'figures.tasks.update_enrollment_data': 'edx.lms.core.high_mem',
            'figures.tasks.populate_monthly_metrics_for_site': 'edx.lms.core.high_mem',
        }