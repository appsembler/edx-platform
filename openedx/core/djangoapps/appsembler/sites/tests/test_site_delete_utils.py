from unittest.mock import patch

import pytest
import tahoe_sites.api
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command, CommandError
from oauth2_provider.models import Application
from organizations.models import OrganizationCourse
from status.models import CourseMessage
from student.models import AnonymousUserId

from lms.djangoapps.courseware.models import StudentModule
from openedx.core.djangoapps.appsembler.api.tests.factories import (
    CourseOverviewFactory,
    OrganizationCourseFactory,
)
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

from openedx.core.djangoapps.appsembler.sites.deletion_utils import (
    delete_organization_courses,
    delete_site,
    get_models_using_course_key,
    remove_stray_courses_from_mysql,
)

User = get_user_model()


def delete_site_with_patched_cms_imports(red_site):
    """
    Delete a site without running the CMS-related code.
    """
    with patch('openedx.core.djangoapps.appsembler.sites.deletion_utils.remove_course_creator_role'):
        delete_site(red_site)


@pytest.fixture
@pytest.mark.django_db
def make_site(settings):
    settings.DEBUG = True

    def factory(site_color):
        assert settings.ENABLE_COMPREHENSIVE_THEMING
        Application.objects.get_or_create(
            client_id=settings.AMC_APP_OAUTH2_CLIENT_ID,
            client_type=Application.CLIENT_CONFIDENTIAL,
        )

        call_command('create_devstack_site', site_color, 'localhost')

        return Site.objects.get(domain__startswith='{}.'.format(site_color))

    return factory


@pytest.mark.django_db
def test_delete_site(make_site):
    """
    Test `delete_site` happy path.
    """
    red_site = make_site('red')
    delete_site_with_patched_cms_imports(red_site)

    with pytest.raises(User.DoesNotExist):
        User.objects.get(username='red')


@pytest.mark.django_db
def test_delete_one_site_keeps_another(make_site):
    """
    Test `delete_site` with two sites.
    """
    red_site = make_site('red')
    make_site('blue')

    delete_site_with_patched_cms_imports(red_site)

    with pytest.raises(User.DoesNotExist):
        User.objects.get(username='red')

    assert User.objects.get(username='blue'), 'Should not delete other sites'


@pytest.mark.django_db
def test_get_models_using_course_key():
    """
    Test get_models_using_course_key.
    """
    classes = [
        model_class
        for model_class, field in get_models_using_course_key()
    ]

    assert len(classes) > 20, 'Should include a lot of models!'

    assert CourseOverview in classes, 'Should include CourseOverview'
    assert AnonymousUserId in classes, 'Should include AnonymousUserId due to course_id field'
    assert CourseMessage in classes, 'Should include CourseMessage due to course_key field'
    assert OrganizationCourse in classes, 'Should include OrganizationCourse'
    assert StudentModule in classes, 'Should include models with LearningContextKeyField'


@pytest.mark.django_db
def test_delete_course_related_models(make_site):
    """
    Test delete_organization_courses.
    """
    red_site = make_site('red')

    organization = tahoe_sites.api.get_organization_by_site(red_site)
    user = User.objects.get(username='red')

    course = CourseOverviewFactory.create()
    OrganizationCourseFactory.create(
        organization=organization,
        course_id=course.id,
    )
    AnonymousUserId.objects.create(
        user=user,
        course_id=course.id,
        anonymous_user_id='07ee0668-f78d-11ec-a09b-439a1ce0dedf',
    )

    course_related_classes = [
        CourseOverview,
        OrganizationCourse,
        AnonymousUserId,
    ]

    for model_class in course_related_classes:
        assert model_class.objects.get()

    delete_organization_courses(organization)

    for model_class in course_related_classes:
        # Should delete the course-related models
        with pytest.raises(model_class.DoesNotExist):
            model_class.objects.get()


@pytest.mark.django_db
def test_mysql_remove_stray_courses(capsys):
    """
    Tests for the remove_stray_courses_from_mysql with and without courses.
    """
    with pytest.raises(CommandError, match='No courses to delete.'):
        remove_stray_courses_from_mysql(limit=0, commit=False)

    course_key = CourseOverviewFactory.create().id
    assert course_key in CourseOverview.get_all_course_keys(), 'Stray course has been created'

    remove_stray_courses_from_mysql(limit=0, commit=False)
    assert course_key in CourseOverview.get_all_course_keys(), 'Commit=False do not delete the course'
    assert str(course_key) in capsys.readouterr()[0]

    remove_stray_courses_from_mysql(limit=0, commit=True)
    assert course_key not in CourseOverview.get_all_course_keys(), 'Stray course is removed'
    assert str(course_key) in capsys.readouterr()[0]
