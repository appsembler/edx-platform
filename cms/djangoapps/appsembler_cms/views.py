import logging

from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey

from rest_framework import status

from cms.djangoapps.contentstore.utils import reverse_course_url
from contentstore.utils import add_instructor
from enrollment.api import add_enrollment
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.response import Response

from student.models import CourseEnrollment
from xmodule.modulestore.django import modulestore

from appsembler_lms.models import Organization
from appsembler_lms.permissions import SecretKeyPermission
from .serializers import CreateCourseSerializer

logger = logging.getLogger(__name__)
APPSEMBLER_EMAIL = 'support@appsembler.com'


class CreateCourseAPIView(GenericAPIView):
    permission_classes = (SecretKeyPermission,)
    serializer_class = CreateCourseSerializer

    def post(self, *args, **kwargs):
        serializer = self.get_serializer(data=self.request.data)
        if serializer.is_valid():
            try:
                user = User.objects.get(email=serializer.data.get('email'))
            except User.DoesNotExist:
                message = "User does not exist in academy.appsembler.com"
                return Response(status=status.HTTP_404_NOT_FOUND, data=message)

            store_for_new_course = modulestore()
            org = get_object_or_404(Organization, key=serializer.data.get('organization_key'))
            number = "{}101".format(user.username)
            run = "CurrentTerm"
            fields = {
                "display_name": "{}'s First Course".format(user.profile.name)
            }
            try:
                source_course_key = CourseKey.from_string("course-v1:edX+DemoX+Demo_Course")
                destination_course_key = CourseKey.from_string("course-v1:{}+{}+{}".format(org.key, number, run))
                new_course = store_for_new_course.clone_course(source_course_key, destination_course_key, user.username, fields)
                new_course_url = reverse_course_url('course_handler', new_course.id)
                add_instructor(new_course.id, User.objects.get(email="staff@example.com"), user)
                CourseEnrollment.enroll(user, new_course.id, mode='honor')
                response_data = {
                    'course_url': new_course_url
                }
                return Response(status=status.HTTP_201_CREATED, data=response_data)
            except Exception as e:
                message = "Unable to create new course."
                logger.error(message)
        return Response(status=status.HTTP_400_BAD_REQUEST)

create_course_endpoint = CreateCourseAPIView.as_view()
