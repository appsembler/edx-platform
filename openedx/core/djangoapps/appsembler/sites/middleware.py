from django.conf import settings
from django.core.cache import cache, caches
from django.contrib.redirects.models import Redirect
from django.shortcuts import redirect

from openedx.core.djangoapps.appsembler.sites.models import AlternativeDomain

import beeline
import logging
log = logging.getLogger(__name__)


class CustomDomainsRedirectMiddleware(object):

    @beeline.traced(name="CustomDomainsRedirectMiddleware.process_request")
    def process_request(self, request):
        cache_general = caches['default']
        hostname = request.get_host()
        if hostname.endswith(settings.SITE_NAME):
            cache_key = '{prefix}-{site}'.format(prefix=settings.CUSTOM_DOMAINS_REDIRECT_CACHE_KEY_PREFIX, site=hostname)
            custom_domain = cache_general.get(cache_key)
            if custom_domain is None:
                beeline.add_context_field("custom_domain_cache_hit", False)
                try:
                    alternative_domain = AlternativeDomain.objects.select_related('site').get(domain=hostname)
                    custom_domain = alternative_domain.site.domain
                except AlternativeDomain.DoesNotExist:
                    custom_domain = ""
                cache_general.set(cache_key, custom_domain, settings.CUSTOM_DOMAINS_REDIRECT_CACHE_TIMEOUT)
            else:
                beeline.add_context_field("custom_domain_cache_hit", True)

            if custom_domain:
                beeline.add_context_field("custom_domain_perform_redirect", True)
                return redirect("https://" + custom_domain)
            else:
                beeline.add_context_field("custom_domain_perform_redirect", False)

            return


class RedirectMiddleware(object):
    """
    Redirects requests for URLs persisted using the django.contrib.redirects.models.Redirect model.
    With the exception of the main site.
    """
    @beeline.traced(name="RedirectMiddleware.process_request")
    def process_request(self, request):
        """
        Redirects the current request if there is a matching Redirect model
        with the current request URL as the old_path field.
        """
        site = request.site
        try:
            beeline.add_context_field("site_id", site.id)
            in_whitelist = any(map(
                lambda p: p in request.path,
                settings.MAIN_SITE_REDIRECT_WHITELIST))
            if (site.id == settings.SITE_ID) and not in_whitelist:
                beeline.add_context_field("unknown_site_redirect", True)
                return redirect("https://appsembler.com/tahoe/")
        except Exception:
            # I'm not entirely sure this middleware get's called only in LMS or in other apps as well.
            # Soooo just in case
            beeline.add_context_field("redirect_middleware_exception", True)
            pass
        cache_key = '{prefix}-{site}'.format(prefix=settings.REDIRECT_CACHE_KEY_PREFIX, site=site.domain)
        redirects = cache.get(cache_key)
        if redirects is None:
            redirects = {redirect.old_path: redirect.new_path for redirect in Redirect.objects.filter(site=site)}
            cache.set(cache_key, redirects, settings.REDIRECT_CACHE_TIMEOUT)
        redirect_to = redirects.get(request.path)
        if redirect_to:
            return redirect(redirect_to, permanent=True)
