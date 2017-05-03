from django.conf.urls import url

from . import API_VERSION, views

urlpatterns = [
    url(r'^$', views.SearchIndex.as_view(), name='search_api_index'),
    url(r'^{}/reindex-course'.format(API_VERSION),
        views.CourseIndexer.as_view(), name='reindex-course'),
    url(r'^{}/register-facet'.format(API_VERSION),
        views.FacetRegister.as_view(), name='register-facet')
]
