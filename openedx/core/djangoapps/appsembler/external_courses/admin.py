from django.contrib import admin

from openedx.core.djangoapps.appsembler.external_courses.models import ExternalCourseTile


@admin.register(ExternalCourseTile)
class ExternalCourseTileAdmin(admin.ModelAdmin):

    fields = ('course_duration', 'course_key', 'title', 'org', 'course_link', 'image_url', 'starts', 'ends', 'pacing_type', 'is_credit_eligible', 'is_verified_eligible')
    readonly_fields = ('course_key', 'title', 'org', 'course_link', 'image_url', 'starts', 'ends', 'pacing_type', 'is_credit_eligible', 'is_verified_eligible')

    class Meta:
        verbose_name = "External Course"
        verbose_name_plural = "External Courses"
