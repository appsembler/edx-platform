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
        self.site = SiteFactory(domain='foo.test')
        self.organization = OrganizationFactory(sites=[self.site])


    # def test_get_course_keys_for_site(self, course_count):
    def test_get_course_keys_for_site(self):
        course_count = 2
        course_overviews = [CourseOverviewFactory() for i in range(course_count)]
        for co in course_overviews:
            OrganizationCourseFactory(organization=self.organization,
                                      course_id=str(co.id))
        course_keys = aapi_sites.get_course_keys_for_site(self.site)
        expected_ids = [str(co.id) for co in course_overviews]


@pytest.mark.django_db
class TestSiteModule(object):
    """
    Tests figures.sites site handling functions in multisite mode

    Assumptions:
    * We're using Appsembler's fork of `edx-organizations` for the multisite
      tests

    """
    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        self.site = SiteFactory(domain='foo.test')
        self.organization = OrganizationFactory(sites=[self.site])
        assert Site.objects.count() == 2

    # def test_get_site_for_courses(self):
    #     """
    #     Can we get the site for a given course?

    #     We shouldn't care what the other site is. For reference, it is the
    #     default site with 'example.com' for both the domain and name fields
    #     """
    #     # We want to move the patch to the class level if possible

    #     co = CourseOverviewFactory()
    #     OrganizationCourseFactory(organization=self.organization,
    #                               course_id=str(co.id))
    #     site = aapi_sites.get_site_for_course(str(co.id))
    #     assert site == self.site

    # def test_get_site_for_course_not_in_site(self):
    #     """
    #     We create a course but don't add the course to OrganizationCourse
    #     We expect that a site cannot be found
    #     """
    #     co = CourseOverviewFactory()
    #     site = aapi_sites.get_site_for_course(str(co.id))
    #     assert not site

    # @pytest.mark.parametrize('course_id', ['', None])
    # def test_get_site_for_non_existing_course(self, course_id):
    #     """
    #     We expect no site returned for None for the course
    #     """
    #     site = aapi_sites.get_site_for_course(course_id)
    #     assert not site

    @pytest.mark.parametrize('course_count', [0, 1, 2])
    def test_get_course_keys_for_site(self, course_count):

        course_overviews = [CourseOverviewFactory() for i in range(course_count)]
        for co in course_overviews:
            OrganizationCourseFactory(organization=self.organization,
                                      course_id=str(co.id))
        course_keys = aapi_sites.get_course_keys_for_site(self.site)
        expected_ids = [str(co.id) for co in course_overviews]
        assert set([str(key) for key in course_keys]) == set(expected_ids)

    @pytest.mark.parametrize('course_count', [0, 1, 2])
    def test_get_courses_for_site(self, course_count):
        course_overviews = [CourseOverviewFactory() for i in range(course_count)]
        for co in course_overviews:
            OrganizationCourseFactory(organization=self.organization,
                                      course_id=str(co.id))
        courses = aapi_sites.get_courses_for_site(self.site)
        expected_ids = [str(co.id) for co in course_overviews]
        assert set([str(co.id) for co in courses]) == set(expected_ids)

    # @pytest.mark.parametrize('ce_count', [0, 1, 2])
    # def test_get_course_enrollments_for_site(self, ce_count):

    #     course_overview = CourseOverviewFactory()
    #     OrganizationCourseFactory(organization=self.organization,
    #                               course_id=str(course_overview.id))
    #     expected_ce = [CourseEnrollmentFactory(
    #         course_id=course_overview.id) for i in range(ce_count)]
    #     course_enrollments = aapi_sites.get_course_enrollments_for_site(self.site)
    #     assert set([ce.id for ce in course_enrollments]) == set(
    #                [ce.id for ce in expected_ce])
