from __future__ import absolute_import, unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from souvenirs.reports import (daily_usage, customer_monthly_usage,
                               customer_quarterly_usage,
                               customer_yearly_usage,
                               calendar_monthly_usage)
from openedx.core.djangoapps.appsembler.usage.models import (
    Customer, UsageDaily, UsageCustomerMonthly, UsageCustomerQuarterly,
    UsageCustomerYearly, UsageCalendarMonthly)
from ._helpers import DateAction


class Command(BaseCommand):
    help = "Aggregates usage data to Google Cloud SQL for reports"

    def add_arguments(self, parser):
        parser.add_argument('--customer-id', metavar='STR', required=True)
        parser.add_argument('--customer-name', metavar='STR', required=True)
        parser.add_argument('--subscription-start', metavar='DATE',
                            action=DateAction, required=True)
        parser.add_argument('--quota', metavar='NUM', type=int, default=0)
        parser.add_argument('--force', action='store_true',
                            help="delete customer and re-insert, instead of upsert")

    def handle(self, *args, **options):
        if '__' not in options['customer_id']:
            raise CommandError("--customer-id should be of the form box__customer")

        self.sanity_check(options)

        # this cascades to delete all the related usage rows
        if options['force']:
            Customer.objects.filter(id=options['customer_id']).delete()

        customer, _ = Customer.objects.update_or_create(
            id=options['customer_id'],
            defaults=dict(
                name=options['customer_name'],
                quota=options['quota'],
            ),
        )

        # track how many rows we add
        added = updated = 0

        # set a common end-time for consistency between tables
        end = timezone.now()

        for d in daily_usage(options['subscription_start'], end=end):
            _, created = UsageDaily.objects.update_or_create(
                customer=customer,
                date=d['period']['start'].date(),
                defaults=dict(
                    map_fields(d),
                    label_year_month=d['labels']['year_month'],
                    label_year_quarter=d['labels']['year_quarter'],
                    label_year=d['labels']['year'],
                ),
            )
            if created:
                added += 1
            else:
                updated += 1

        for d in customer_monthly_usage(options['subscription_start'], end=end):
            _, created = UsageCustomerMonthly.objects.update_or_create(
                customer=customer,
                label_year_month=d['labels']['year_month'],
                defaults=dict(
                    map_fields(d),
                    label_year_quarter=d['labels']['year_quarter'],
                    label_year=d['labels']['year'],
                ),
            )
            if created:
                added += 1
            else:
                updated += 1

        for d in customer_quarterly_usage(options['subscription_start'], end=end):
            _, created = UsageCustomerQuarterly.objects.update_or_create(
                customer=customer,
                label_year_quarter=d['labels']['year_quarter'],
                defaults=dict(
                    map_fields(d),
                    label_year=d['labels']['year'],
                ),
            )
            if created:
                added += 1
            else:
                updated += 1

        for d in customer_yearly_usage(options['subscription_start'], end=end):
            _, created = UsageCustomerYearly.objects.update_or_create(
                customer=customer,
                label_year=d['labels']['year'],
                defaults=map_fields(d),
            )
            if created:
                added += 1
            else:
                updated += 1

        for d in calendar_monthly_usage(options['subscription_start'], end=end):
            _, created = UsageCalendarMonthly.objects.update_or_create(
                customer=customer,
                label_calendar_year_month=d['labels']['calendar_year_month'],
                defaults=dict(
                    map_fields(d),
                    label_calendar_year=d['labels']['calendar_year'],
                ),
            )
            if created:
                added += 1
            else:
                updated += 1

        return 'added {added} rows\nupdated {updated} rows'.format(
            added=added, updated=updated)

    def sanity_check(self, options):
        # if the subscription start date changes, then it's no longer safe to
        # use upserts which are based on row labels such as "Y01 M01".
        d = UsageDaily.objects.filter(customer_id=options['customer_id']) \
                              .order_by('period_start') \
                              .first()
        if (d and d.period_start != options['subscription_start'] and
                not options['force']):
            raise CommandError("--subscription-start changed, use --force if you're sure.")


def map_fields(d):
    # period_start=d['period']['start'],
    # period_end=d['period']['end'],
    # sum_registered_users=d['usage']['registered_users']
    # sum_activated_users=d['usage']['activated_users']
    # sum_active_users=d['usage']['active_users']
    # sum_registered_admins=d['usage']['registered_admins']
    # sum_activated_admins=d['usage']['activated_admins']
    # sum_active_admins=d['usage']['active_admins']
    # sum_registered_staff=d['usage']['registered_staff']
    # sum_activated_staff=d['usage']['activated_staff']
    # sum_active_staff=d['usage']['active_staff']
    # sum_registered_instructors=d['usage']['registered_instructors']
    # sum_activated_instructors=d['usage']['activated_instructors']
    # sum_active_instructors=d['usage']['active_instructors']
    # sum_registered_learners=d['usage']['registered_learners']
    # sum_activated_learners=d['usage']['activated_learners']
    # sum_active_learners=d['usage']['active_learners']
    mapped = {'sum_{}'.format(key): value for key, value in d['usage'].items()}
    mapped.update(
        period_start=d['period']['start'],
        period_end=d['period']['end'],
    )
    return mapped
