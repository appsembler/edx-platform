"""
Testing multi-tenant CERTIFICATES_HTML_VIEW feature flag.
"""
import pytest
from organizations.models import OrganizationCourse

from cms.djangoapps.contentstore.views.certificates import CertificateManager
from openedx.core.djangoapps.appsembler.api.tests.factories import CourseOverviewFactory
from openedx.core.djangoapps.site_configuration.tests.factories import SiteConfigurationFactory

from tahoe_sites.api import create_tahoe_site


@pytest.fixture
def create_course_with_site_configuration(settings):
    """
    Factory for course with its related site configuration.
    """
    def _create_course_with_site_configuration(configs):
        # Ensure SiteConfiguration.save() works
        settings.DEFAULT_SITE_THEME = 'edx-theme-codebase'

        course = CourseOverviewFactory.create()

        # Simulate configured certificates in the course
        course.certificates = {'certificates': [{'is_active': True}]}

        # Create Tahoe 2.0 site/organization pair.
        org_data = create_tahoe_site(short_name=course.org, domain='test.com')

        # Link the course to the organization
        OrganizationCourse.objects.create(course_id=course.id, organization=org_data['organization'])

        # Create site configuration
        site_config = SiteConfigurationFactory.create(
            site=org_data['site'],
            site_values={
                'course_org_filter': course.org,
                **configs,
            }  # Allow `get_all_org` to work
        )

        return {
            'course': course,
            'site_configuration': site_config,
            **org_data,
        }

    return _create_course_with_site_configuration


@pytest.mark.django_db
@pytest.mark.parametrize('feature_flag', [False, True])
def test_html_certificate_feature_flag_enabled(feature_flag, create_course_with_site_configuration):
    """
    Ensure CERTIFICATES_HTML_VIEW can be enabled via SiteConfiguration.
    """
    course_data = create_course_with_site_configuration({
        'CERTIFICATES_HTML_VIEW': feature_flag
    })
    course = course_data['course']

    is_active, _certificates = CertificateManager.is_activated(course=course)
    assert is_active == feature_flag, 'Should match the feature flag.'
