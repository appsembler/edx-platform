
from rest_framework import serializers

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

class CourseOverviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = CourseOverview
        fields = (
            'id', 'display_name', 'org',
        )
