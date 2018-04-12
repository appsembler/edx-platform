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


class SearchIndex(APIView):
    authentication_classes = (
        BasicAuthentication,
        SessionAuthentication,
        TokenAuthentication
    )

    permission_classes = (IsAuthenticated, IsStaffUser, )

    def get(self, request, format=None):
        return Response({
            'message': 'CMS Search API',
        })


class CourseIndexer(APIView):
    authentication_classes = (
        BasicAuthentication,
        SessionAuthentication,
        TokenAuthentication
    )

    permission_classes = (IsAuthenticated, IsStaffUser, )

    def get(self, request, format=None):
        return Response({
            'message': 'Course Indexer',
        })

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
            response = Response(response_data)
            response['Access-Control-Allow-Origin'] = ALLOWED_ORIGIN
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response['Access-Control-Allow-Headers'] = '*'
            return response
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

    def options(self, request, format=None):
        response = Response()
        response['Access-Control-Allow-Origin'] = ALLOWED_ORIGIN
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        # Options do not allow wildcard for access-control-allow-headers
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
