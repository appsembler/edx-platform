
import argparse
import os
import sys
import traceback

from django.core.management.base import BaseCommand, CommandError

from django.contrib.sites.models import Site

from microsite_configuration.models import Microsite, MicrositeOrganizationMapping
from organizations import api as orgsApi

from hr_management.utils import delete_microsite

class Command(BaseCommand):
    help = 'delete the specified microsite'

    def add_arguments(self, parser):
        parser.add_argument('microsite', nargs='+', type=str)

    def handle(self, *args, **options):
        for microsite in options['microsite']:
            try:
                # Get the query set for microsites
                microsite_qs = Microsite.objects.filter(key=microsite)
                # We assume we are going to get a QuerySet object
                if microsite_qs.count() == 1:
                    print("going to delete microsite: {}".format(microsite))
                    result = delete_microsite(microsite_qs[0])
                    if result == True:
                        print("deleted microsite and mapping for {}".format(microsite))
                    else:
                        print("unable to delete microsite for {}".format())
                elif microsite_qs.count() > 1:
                    raise "to many microsites for key: {}".format(microsite)
                elif microsite_qs.count() == 0:
                    print("Cannot find microsite with name '{}'".format(microsite))
                else:
                    raise "Error, how did we get negative count?. query count={}".format(microsite_qs.count())
            except: # Trap all exceptions
                e = sys.exc_info()[0]
                print("Error finding microsites: {}".format(e))
                traceback.print_exc(file=sys.stdout)
