import os
import logging


from django.conf import settings
from django.conf.urls import include, url


SERVICE_URLS_INCLUDES = {
    'lms': 'LMS_URLS_INCLUDE',
    'cms': 'CMS_URLS_INCLUDE',
}

service_variant = os.environ.get('SERVICE_VARIANT', None)
urls_include_conf = SERVICE_URLS_INCLUDES[service_variant]
urlpatterns = ()

if hasattr(settings, 'APPSEMBLER_FEATURES') and \
        settings.APPSEMBLER_FEATURES.get(urls_include_conf, False):

    for url_include in settings.APPSEMBLER_FEATURES[urls_include_conf]:
        try:
            # members of *_URLS_INCLUDE should be a list
            # of format regex, dotted path
            if type(url_include).__name__ == 'list':
                regex = url_include[0]
                dotted_path = url_include[1]
                urlpatterns += (url(regex, include(dotted_path)), )
            else:
                raise TypeError

        except (ImportError, TypeError):
            logger = logging.getLogger(__name__)
            logger.warn('lms.urls Could not import urls from {}.  Ignoring.'.format(dotted_path))
