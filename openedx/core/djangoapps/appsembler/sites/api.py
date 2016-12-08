from django.contrib.sites.models import Site
from django.core.files.storage import DefaultStorage
from rest_framework import generics, views, viewsets, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
from .serializers import (SiteConfigurationSerializer, SiteConfigurationListSerializer,
        SiteSerializer, RegistrationSerializer)
from .tasks import bootstrap_site, delete_site


class SiteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Site.objects.exclude(configuration=None)
    serializer_class = SiteSerializer


class SiteConfigurationViewSet(viewsets.ModelViewSet):
    queryset = SiteConfiguration.objects.all()
    serializer_class = SiteConfigurationSerializer
    list_serializer_class = SiteConfigurationListSerializer
    create_serializer_class = SiteSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return self.list_serializer_class
        if self.action == 'create':
            return self.create_serializer_class
        return super(SiteConfigurationViewSet, self).get_serializer_class()

    def perform_destroy(self, instance):
        delete_site.delay(instance)


class FileUploadView(views.APIView):
    parser_classes = (MultiPartParser,)

    def post(self, request, format=None):
        file_obj = request.data['file']
        file_path = self.handle_uploaded_file(file_obj, request.GET.get('filename'))
        return Response({'file_path': file_path}, status=201)

    def handle_uploaded_file(self, content, filename):
        storage = DefaultStorage()
        name = storage.save(filename, content)
        return storage.url(name)


class SiteCreateView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer


class TaskResultView(views.APIView):
    def get(self, request, format=None):
        task_id = self.kwargs['task_id']
        result = bootstrap_site.AsyncResult(task_id)
        if result.ready():
            ret = result.get()
            return Response(ret)
        else:
            # TODO: We probably should return a different error code here
            return Response(status=status.HTTP_404_NOT_FOUND)

