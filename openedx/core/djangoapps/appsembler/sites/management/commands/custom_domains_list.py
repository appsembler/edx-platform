import json

from openedx.core.djangoapps.appsembler.sites.models import AlternativeDomain

from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Outputs the list of custom domains that will be used to generate let's encrypt certs"

    def handle(self, *args, **options):
        altertive_domains = AlternativeDomain.objects.values_list('site__domain', flat=True)
        domains = [{'domains': [domain]} for domain in altertive_domains]
        self.stdout.write(json.dumps(domains))
