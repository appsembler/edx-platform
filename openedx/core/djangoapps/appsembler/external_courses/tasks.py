"""
Code to manage fetching and storing courses from external sources.
"""

from celery.task import task
import logging
import requests
from dateutil.parser import parse

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from django.conf import settings

from openedx.core.djangoapps.appsembler.external_courses.models import ExternalCourseTile

log = logging.getLogger(__name__)


@task(name='openedx.core.djangoapps.appsembler.external_courses.tasks.fetch_courses')
def fetch_courses():

    num_changed = 0
    num_added = 0
    num_failed = 0
    num_deleted = 0

    if not settings.EDX_ORG_COURSE_API_CATALOG_IDS:
        raise Exception("EDX_ORG_COURSE_API_CATALOG_IDS variable is undefined")

    for catalog_id in settings.EDX_ORG_COURSE_API_CATALOG_IDS:
        client = BackendApplicationClient(
            client_id=settings.EDX_ORG_COURSE_API_CLIENT_ID
        )
        oauth = OAuth2Session(client=client)
        token = oauth.fetch_token(
            token_url=settings.EDX_ORG_COURSE_API_TOKEN_URL,
            client_id=settings.EDX_ORG_COURSE_API_CLIENT_ID,
            client_secret=settings.EDX_ORG_COURSE_API_CLIENT_SECRET,
            token_type=settings.EDX_ORG_COURSE_API_TOKEN_TYPE
        )
        headers = {
            'Content-Type': 'application/json',
            'Authorization': '{token_type} {token}'.format(
                token_type=settings.EDX_ORG_COURSE_API_TOKEN_TYPE,
                token=token['access_token']
            )
        }
        response = requests.get(
            '{api_url}api/v1/catalogs/{catalog_id}/courses/?limit=100&offset=0'.format(
                api_url=settings.EDX_ORG_COURSE_API_URL,
                catalog_id=catalog_id
            ),
            headers=headers)

        if response.status_code != 200:
            log.info(
                'Error in request, the endpoint returned an invalid status code: {code} for the catalog id: {catalog_id}'.format(
                    code=response.status_code, catalog_id=catalog_id
                )
            )
            continue

        if not response.json()['results'] or len(response.json()['results']) <= 0:
            log.info('No results were found for catalog %s' % catalog_id)
            continue

        for course in response.json()['results']:

            course_key = course['key']

            try:
                obj_course = ExternalCourseTile.objects.get(
                    course_key=course_key)
                is_new = False
            except ExternalCourseTile.DoesNotExist:
                obj_course = ExternalCourseTile(course_key=course_key)
                is_new = True

            if len(course['course_runs']) < 1 or course['owners'] < 1:  # assuming no run or no owners
                if not is_new:
                    obj_course.delete()
                    num_deleted += 1
                continue

            course_run = course['course_runs'][0]

            try:
                obj_course.title = course['title']
                obj_course.org = course['owners'][0]['key']
                obj_course.course_link = course_run['marketing_url']
                obj_course.image_url = course_run['image']['src']
                obj_course.starts = parse(course_run['start'])
                obj_course.ends = parse(course_run['end'])
                obj_course.pacing_type = course_run['pacing_type']

                if 'seats' in course_run:
                    for seat in course_run['seats']:
                        if seat['type'] == 'credit':
                            obj_course.is_credit_eligible = True
                        elif seat['type'] == 'verified':
                            obj_course.is_verified_eligible = True

                obj_course.save()

                if is_new:
                    num_added += 1
                else:
                    num_changed += 1

            except:
                log.info('Import course failed: ' + course_key)
                num_failed += 1

    return (num_added, num_changed, num_failed, num_deleted, (num_added + num_changed + num_failed + num_deleted))


def is_credit_eligible(course_run):
    """
    Inspect the course seat to check if the course is credit eligible
    :param json_course: The JSON course item
    :return: boolean
    """
    for seat in course_run['seats']:
        if seat['type'] == 'credit':
            return True

    return False
