"""
Site-aware Tahoe cache utils.
"""

TAHOE_LAST_CONFIG_UPDATE_KEY_FMT = 'tahoe_config_update.{site_domain}'


def refresh_tahoe_config_key(site_domain, now=None):
    if not now:
        from django.utils import timezone
        now = timezone.now()

    now = str(now)

    cache_key = TAHOE_LAST_CONFIG_UPDATE_KEY_FMT.format(site_domain=site_domain)
    cache.set(cache_key, now)
    return now


def get_tahoe_last_config_update(site_domain, now=None):
    cache_key = TAHOE_LAST_CONFIG_UPDATE_KEY_FMT.format(site_domain=site_domain)

    last_config_update = cache.get(cache_key)

    if not last_config_update:
        last_config_update = refresh_tahoe_config_key(site_domain, now)

    return last_config_update


def suffix_tahoe_cache_key(request, cache_key):
    """
    Suffix the key to clear the cache for old SiteConfigration.
    """
    if hasattr(request, 'site'):
        site_domain = request.site.domain
    else:
        site_domain = 'no_site'

    last_config_update = get_tahoe_last_config_update(site_domain)
    return '{}.{}.'.format(cache_key, last_config_update)
