# URL pattern inclusion from environment config.

Add to `lms.env.config` or `cms.env.config`, in the key 
`APPSEMBLER_FEATURES`, e.g., :

```
"APPSEMBLER_FEATURES": {
    "LMS_URLS_INCLUDE": [
        ["^reporting/", "appsembler_reporting.urls"]
    ] 
}
```

where `"^reporting/"` is the regex for the URL prefix for the included URLs, 
and `"appsembler_reporting.urls"` is the dotted path string to the module containing the urls.  URLs for the LMS should be added to the `LMS_URLS_INCLUDE`key; for the CMS, to `CMS_URLS_INCLUDE`.

The module must contain a `urlpatterns` tuple, and should resemble:

```
from django.conf import settings
from django.conf.urls import include, patterns, url

urlpatterns = patterns(
    'appsembler_reporting.views',
    url(r'^$','index', name='index'),
    url(r'^download$','download', name='download'),
)
```

If the module cannot be imported, the URLs will be skipped and a warning message will be logged.  
