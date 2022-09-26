"""
URLs for track app
"""
from django.urls import path, re_path

from . import views
from .views import segmentio

urlpatterns = [
    path('event', views.user_track),
    path('segmentio/event', segmentio.segmentio_event),
    re_path(r'^segmentio/send/(?P<method>[a-z]+)$', segmentio.send_event),
]
