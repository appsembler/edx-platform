from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from rest_framework import serializers

from student.roles import (
    REGISTERED_ACCESS_ROLES,
    CourseRole,
)


COURSE_ROLES = [
    role_class for role_class in REGISTERED_ACCESS_ROLES.values()
    if issubclass(role_class, CourseRole)
]


class StringListField(serializers.ListField):
    def to_internal_value(self, data):
        return data.split(',')


class BulkEnrollmentSerializer(serializers.Serializer):
    identifiers = serializers.CharField(required=True)
    courses = StringListField(required=True)
    action = serializers.ChoiceField(
        choices=(
            ('enroll', 'enroll'),
            ('unenroll', 'unenroll')
        ),
        required=True
    )
    auto_enroll = serializers.BooleanField(default=False)
    email_students = serializers.BooleanField(default=False)

    def validate_courses(self, value):
        """
        Check that each course key in list is valid.
        """
        course_keys = value
        for course in course_keys:
            try:
                CourseKey.from_string(course)
            except InvalidKeyError:
                raise serializers.ValidationError("Course key not valid: {}".format(course))
        return value


class CourseRolesSerializer(serializers.Serializer):
    roles = serializers.SerializerMethodField()

    def get_roles(self, course):
        users_by_role = {}

        for role_cls in COURSE_ROLES:
            role = role_cls(course.id)

            users_by_role[role.ROLE] = [{
                'id': user.id,
                'email': user.email,
                'username': user.username,
            } for user in role.users_with_role()]

        return users_by_role
