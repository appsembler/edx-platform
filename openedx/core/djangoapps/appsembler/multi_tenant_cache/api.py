"""
Site-aware Tahoe cache utils.


## Module Objectives ##
Provides a safe way to invalidate site cache immediately upon request.


## API Design ##

suffix_tahoe_cache_key: Used in cache setting logic.
clear_tahoe_site_cache: Used after each configuration update.


## Module Design ##
This module uses the cache (usually `memcache`) twice:

 - Once to store a site-specific update time which is changed via `clear_tahoe_site_cache()`

   >>> cache.get('tahoe_config_update.courses.omardo.com') == '2022-08-04 15:23:28.914059+00:00'

 - Another time is to suffix cache_keys for site specfic caches via `suffix_tahoe_cache_key()`.
   For example `cache_if_anonymous` key would be changed from:
   >>> page_cache_key = domain + ":cache_if_anonymous." + request.path
   >>> page_cache_key == 'courses.omardo.com:cache_if_anonymous./about'

   To

   >>> page_cache_key = suffix_tahoe_cache_key(domain + ":cache_if_anonymous." + request.path)
   >>> page_cache_key == 'courses.omardo.com:cache_if_anonymous./about.2022-08-04 15:23:28.914059+00:00'


## Alternative Designs ##

### Design 2: Delete by namespace
The most obvious way is to have cache.delete_prefix('courses.omardo.com.*') method in Django.
However, such method don't exist for cache design reason in Django.

This module exists to overcome this limitation based on memcache recommendation of deleting by namespace:

 - https://github.com/memcached/memcached/wiki/ProgrammingTricks#deleting-by-namespace


### Design 3: Store the update time in database
This solution requires adding another SiteConfigLastUpdate(Model) class to store the latest update time.

This solution was dimissed to avoid adding yet another model to Open edX.

"""
from django.core import cache as django_cache

try:
    cache = django_cache.caches['general']
except Exception:
    cache = django_cache.cache


__all__ = ['clear_tahoe_site_cache', 'suffix_tahoe_cache_key']


def clear_tahoe_site_cache(site_domain, now=None):
    """
    Set the Tahoe Config update time to clear cache.
    """
    if not now:
        from django.utils import timezone
        now = timezone.now()

    now = str(now)

    cache_key = build_tahoe_config_update_time_cache_key(site_domain)
    cache.set(cache_key, now)
    return now


def suffix_tahoe_cache_key(request_site, cache_key):
    """
    Suffix the key to clear the cache for old SiteConfiguration.

    Provides cache-invalidating suffix that changes after each SiteConfiguration
    update or CSS compile.
    """
    site_domain = getattr(request_site, 'domain', 'no_site')
    last_config_update = get_tahoe_config_update_time(site_domain)
    return '{}.{}.'.format(cache_key, last_config_update)


def build_tahoe_config_update_time_cache_key(site_domain):
    """
    Helper to build site config last update time cache key.
    """
    return 'tahoe_config_update:{site_domain}'.format(site_domain=site_domain)


def get_tahoe_config_update_time(site_domain, now=None):
    """
    Read the latest update time for the site's config.
    """
    cache_key = build_tahoe_config_update_time_cache_key(site_domain)

    last_config_update = cache.get(cache_key)

    if not last_config_update:
        last_config_update = clear_tahoe_site_cache(site_domain, now)

    return last_config_update
