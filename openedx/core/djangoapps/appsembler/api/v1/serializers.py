
from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework.authtoken.models import Token

from organizations.models import UserOrganizationMapping

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

from openedx.core.djangoapps.appsembler.api.helpers import as_course_key
# from openedx.core.djangoapps.appsembler.api.sites import is_admin_for_site


class StringListField(serializers.ListField):
    child = serializers.CharField()


class CourseOverviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = CourseOverview
        fields = (
            'id', 'display_name', 'org',
        )


class BulkEnrollmentSerializer(serializers.Serializer):
    identifiers = StringListField(allow_empty=False)
    courses = StringListField(allow_empty=False)
    action = serializers.ChoiceField(
        choices=(
            ('enroll', 'enroll'),
            ('unenroll', 'unenroll')
        ),
        required=True
    )
    auto_enroll = serializers.BooleanField(default=False)
    email_learners = serializers.BooleanField(default=False)

    def validate_courses(self, value):
        """
        Check that each course key in list is valid.

        Will raise `serializers.ValidationError` if any exceptions found in
        converting to a `CourseKey` instance
        """
        course_keys = value
        for course in course_keys:
            try:
                as_course_key(course)
            except:
                raise serializers.ValidationError("Course key not valid: {}".format(course))
        return value

    def validate_identifiers(self, value):

        if not isinstance(value, (list, tuple)):
            raise serializers.ValidationError(
                'identifiers must be a list, not a {}'.format(type(value)))
        # TODO: Do we want to enforce identifier type (like email, username)
        return value


class TahoeApiKeyDetailSerializer(serializers.Serializer):
    """Serializer to provide data needed for a user. Primary use is in the
    Tahoe API Key Management detail view
    """
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    created = serializers.DateTimeField(required=False)
    secret = serializers.CharField(required=False)

    class Meta:
        fields = ['user_id', 'username', 'created', 'secret', ]
        read_only_fields = fields


class TahoeApiKeyListSerializer(serializers.ModelSerializer):
    """Serializer to provide non-secret Tahoe API key data
    Primary use is in the Tahoe API Key Management list view

    Future functionality would include metadata

    We don't wan to share the secret in this serializer, nor any data which we
    would NOT want visible to a site administrator
    """
    user_id = serializers.IntegerField(source='id')
    username = serializers.CharField()
    token_created = serializers.DateTimeField(source='auth_token.created')

    class Meta:
        model = get_user_model()
        fields = ['user_id', 'username', 'token_created', ]
        read_only_fields = fields


class UserIndexSerializer(serializers.ModelSerializer):
    """Provides a limited set of user information for summary display
    """
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    fullname = serializers.CharField(
        source='profile.name', default=None, read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            'id', 'username', 'fullname', 'email',
        )
