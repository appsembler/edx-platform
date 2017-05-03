
import functools
import json

from django.conf import settings 
from django.http import HttpResponse

from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from opaque_keys import InvalidKeyError

from . import api
from .permissions import IsStaffUser

# Restrict access to the LMS server
ALLOWED_ORIGIN = settings.LMS_BASE

description = """
Appembler Open edX search api. 
Opens up access to Open edX'sa search infrastructure via HTTP (REST) API interfaces.
"""

def cors_headers(original_function=None,
    allow_origin=ALLOWED_ORIGIN,
    allow_methods='GET, POST, OPTIONS',
    allow_headers='*'):
    """ Decorator to simplify and dry up the code.

    TODO: Review for replacement by a popular library or move this somewhere
    that makes sense for common use

    """
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            response = function(*args, **kwargs)
            response['Access-Control-Allow-Origin'] = allow_origin
            response['Access-Control-Allow-Methods'] = allow_methods
            response['Access-Control-Allow-Headers'] = allow_headers
            return response
        return wrapper
    return decorator(original_function) if original_function else decorator


class OptionsMixin(object):
    @cors_headers(allow_headers='Content-Type')
    def options(self, request, format=None):
        return Response()

class SearchBaseAPIView(APIView):
    authentication_classes = (
        BasicAuthentication,
        SessionAuthentication,
        TokenAuthentication
    )

    permission_classes = ( IsAuthenticated, IsStaffUser, )


class SearchIndex(SearchBaseAPIView):

    def get(self, request, format=None):
        return Response({
            'message': 'CMS Search API',
            })


class CourseIndexer(OptionsMixin, SearchBaseAPIView):

    def get(self, request, format=None):
        return Response({
            'message': 'Course Indexer',
            })

    @cors_headers
    def post(self, request, format=None):

        request_data = json.loads(request.body)
        course_id = request_data.get('course_id')
        try:
            results = api.reindex_course(course_id)
            response_data = {
                'course_id': course_id,
                'status': 'OK',
                'message': 'course reindex initiated',
                'results': results,
            }
            return Response(response_data)

        except Exception as e:
            if isinstance(e, InvalidKeyError):
                message = 'InvalidKeyError: Cannot find key for course string ' + \
                    '"{}"'.format(course_id)
                status = 400
            else:
                message = 'Exception "{}" msg: {}'.format(e.__class__, e.message)
                status = 500
            return Response(json.dumps({
                    'course_id': course_id,
                    'status': 'ERROR',
                    'message': message,
                }), status=status)


class FacetRegister(OptionsMixin, SearchBaseAPIView):

    @cors_headers
    def post(self, request, format=None):

        request_data = json.loads(request.body)
        facet_slug = request_data.get('facet_slug')
        try:
            about_info_obj = api.register_facet(facet_slug=facet_slug)
            response_data = {
                'facet_slug': facet_slug,
                'status': 'OK',
                'message': 'Facet registered',
            }
            return Response(response_data)

        except Exception as e:
            message = 'Exception "{}" msg: {}'.format(e.__class__, e.message)
            return Response(json.dumps({
                    'facet_slug': facet_slug,
                    'status': 'ERROR',
                    'message': message,
                }), status=500)
