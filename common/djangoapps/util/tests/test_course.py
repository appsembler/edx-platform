"""
Tests for course utils.
"""


import ddt
import mock
from django.conf import settings

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from util.course import get_link_for_about_page
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory


@ddt.ddt
class TestCourseSharingLinks(ModuleStoreTestCase):
    """
    Tests for course sharing links.
    """
    def setUp(self):
        super(TestCourseSharingLinks, self).setUp()

        # create test mongo course
        self.course = CourseFactory.create(
            org='test_org',
            number='test_number',
            run='test_run',
            default_store=ModuleStoreEnum.Type.split,
            social_sharing_url='test_social_sharing_url',
        )

        # load this course into course overview and set it's marketing url
        self.course_overview = CourseOverview.get_from_id(self.course.id)
        self.course_overview.marketing_url = 'test_marketing_url'
        self.course_overview.save()

    def get_course_sharing_link(self, enable_social_sharing, enable_mktg_site, use_overview=True):
        """
        Get course sharing link.

        Arguments:
            enable_social_sharing(Boolean): To indicate whether social sharing is enabled.
            enable_mktg_site(Boolean): A feature flag to decide activation of marketing site.

        Keyword Arguments:
            use_overview: indicates whether course overview or course descriptor should get
            past to get_link_for_about_page.

        Returns course sharing url.
        """
        mock_settings = {
            'FEATURES': {
                'ENABLE_MKTG_SITE': enable_mktg_site
            },
            'SOCIAL_SHARING_SETTINGS': {
                'CUSTOM_COURSE_URLS': enable_social_sharing
            },
        }

        with mock.patch.multiple('django.conf.settings', **mock_settings):
            course_sharing_link = get_link_for_about_page(
                self.course_overview if use_overview else self.course
            )

        return course_sharing_link

    @ddt.data(
        (True, True, 'test_social_sharing_url'),
        (False, True, 'test_marketing_url'),
        (True, False, 'test_social_sharing_url'),
        (False, False, '{}/courses/course-v1:test_org+test_number+test_run/about'.format('http://test_org.localhost:8000')),
    )
    @ddt.unpack
    def test_sharing_link_with_settings(self, enable_social_sharing, enable_mktg_site, expected_course_sharing_link):
        """
        Verify the method gives correct course sharing url on settings manipulations.
        """
        actual_course_sharing_link = self.get_course_sharing_link(
            enable_social_sharing=enable_social_sharing,
            enable_mktg_site=enable_mktg_site,
        )
        self.assertEqual(actual_course_sharing_link, expected_course_sharing_link)

    @ddt.data(
        (['social_sharing_url'], 'test_marketing_url'),
        (['marketing_url'], 'test_social_sharing_url'),
        (
            ['social_sharing_url', 'marketing_url'],
            '{}/courses/course-v1:test_org+test_number+test_run/about'.format('http://test_org.localhost:8000')
        ),
    )
    @ddt.unpack
    def test_sharing_link_with_course_overview_attrs(self, overview_attrs, expected_course_sharing_link):
        """
        Verify the method gives correct course sharing url when:
         1. Neither marketing url nor social sharing url is set.
         2. Either marketing url or social sharing url is set.
        """
        for overview_attr in overview_attrs:
            setattr(self.course_overview, overview_attr, None)
            self.course_overview.save()

        actual_course_sharing_link = self.get_course_sharing_link(
            enable_social_sharing=True,
            enable_mktg_site=True,
        )
        self.assertEqual(actual_course_sharing_link, expected_course_sharing_link)

    @ddt.data(
        (True, 'test_social_sharing_url'),
        (
            False,
            '{}/courses/course-v1:test_org+test_number+test_run/about'.format('http://test_org.localhost:8000')
        ),
    )
    @ddt.unpack
    def test_sharing_link_with_course_descriptor(self, enable_social_sharing, expected_course_sharing_link):
        """
        Verify the method gives correct course sharing url on passing
        course descriptor as a parameter.
        """
        actual_course_sharing_link = self.get_course_sharing_link(
            enable_social_sharing=enable_social_sharing,
            enable_mktg_site=True,
            use_overview=False,
        )
        self.assertEqual(actual_course_sharing_link, expected_course_sharing_link)
