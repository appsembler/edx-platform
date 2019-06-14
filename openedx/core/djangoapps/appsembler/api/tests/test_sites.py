import mock
import pytest

from django.test import RequestFactory, TestCase

from django.contrib.sites.models import Site

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

import organizations

from openedx.core.djangoapps.site_configuration.tests.factories import (
    SiteConfigurationFactory,
    SiteFactory,
)

from openedx.core.djangoapps.appsembler.api import sites as aapi_sites
from openedx.core.djangoapps.appsembler.api.helpers import as_course_key

from .factories import (
    CourseOverviewFactory,
    OrganizationFactory,
    OrganizationCourseFactory,
    UserOrganizationMappingFactory,
    )


class SitesModuleTests(TestCase):
    def setUp(self):
        """
        The default site already created is u'example.com'
        """
        self.other_site = Site.objects.get(domain=u'example.com')
        self.my_site = SiteFactory(domain='foo.test')
        self.other_site_org = OrganizationFactory(sites=[self.other_site])
        self.my_site_org = OrganizationFactory(sites=[self.my_site])
        self.my_course_overviews = [
            CourseOverviewFactory(),
            CourseOverviewFactory()
        ]
        OrganizationCourseFactory(organization=self.my_site_org,
                                  course_id=str(self.my_course_overviews[0].id))
        OrganizationCourseFactory(organization=self.my_site_org,
                                  course_id=str(self.my_course_overviews[1].id))

        self.other_course_overviews = [CourseOverviewFactory()]
        OrganizationCourseFactory(organization=self.other_site_org,
                                  course_id=str(self.other_course_overviews[0].id))

    def test_get_course_keys_for_site(self):
        course_keys = aapi_sites.get_course_keys_for_site(self.my_site)
        expected_ids = [str(co.id) for co in self.my_course_overviews]
        self.assertEqual(set([str(key) for key in course_keys]), set(expected_ids))

    def test_get_courses_for_site(self):
        courses = aapi_sites.get_courses_for_site(self.my_site)
        expected_ids = [str(co.id) for co in self.my_course_overviews]
        self.assertEqual(set([str(course.id) for course in courses]), set(expected_ids))


    def test_get_site_for_course(self):

        course_id = self.my_course_overviews[0].id
        site = aapi_sites.get_site_for_course(course_id)
        self.assertEqual(site, self.my_site)
