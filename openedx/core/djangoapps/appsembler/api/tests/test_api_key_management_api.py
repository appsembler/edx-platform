
from django.test import TestCase

from django.core.urlresolvers import resolve, reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

import ddt
import mock

from rest_framework.authtoken.models import Token

from openedx.core.djangoapps.site_configuration.tests.factories import (
    SiteFactory,
)
from student.tests.factories import UserFactory

from openedx.core.djangoapps.appsembler.api.tests.factories import (
    OrganizationFactory,
    TokenFactory,
    UserOrganizationMappingFactory,
)


APPSEMBLER_API_VIEWS_MODULE = 'openedx.core.djangoapps.appsembler.api.v1.views'


def create_org_users(org, new_user_count):
    """
    This function is also declared in `test_sites.py` in the user api PR
    We want to define this function in one location
    """
    return [UserOrganizationMappingFactory(
        organization=org).user for i in xrange(new_user_count)]


class TahoeApiBaseViewTest(TestCase):
    def setUp(self):
        super(TahoeApiBaseViewTest, self).setUp()
        self.my_site = SiteFactory(domain='my-site.test')
        self.other_site = SiteFactory(domain='other-site.test')
        self.other_site_org = OrganizationFactory(sites=[self.other_site])
        self.my_site_org = OrganizationFactory(sites=[self.my_site])
        self.caller = UserFactory()
        UserOrganizationMappingFactory(user=self.caller,
                                       organization=self.my_site_org,
                                       is_amc_admin=True)
        self.api_request_factory = APIRequestFactory()

    # def create_get_request(self, url, query_params):
    #     request = self.api_request_factory.get(url)
    #     request.META['HTTP_HOST'] = self.my_site.domain
    #     force_authenticate(request, user=self.caller)
    #     view = resolve(url).func

@ddt.ddt
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.TahoeApiKeyViewSet.throttle_classes', [])
class TahoeApiKeyGetTest(TahoeApiBaseViewTest):

    def setUp(self):
        super(TahoeApiKeyGetTest, self).setUp()

        self.my_site_users = create_org_users(org=self.my_site_org, new_user_count=3)
        self.tokens = [TokenFactory(user=user) for user in self.my_site_users]
        self.other_site_users = create_org_users(org=self.other_site_org, new_user_count=2)

    def test_get_all_tokens(self):
        url = reverse('tahoe-api:v1:api-keys-list')
        request = self.api_request_factory.get(url)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)
        view = resolve(url).func
        response = view(request)
        response.render()
        assert response.status == status.HTTP_200_OK
        results = response.data['results']

    def test_get_token_for_logged_in_user(self):

        caller = UserFactory()
        UserOrganizationMappingFactory(user=caller,
                                       organization=self.my_site_org,
                                       is_amc_admin=True)
        caller_token = TokenFactory(user=caller)
        url = reverse('tahoe-api:v1:api-keys-detail', args=[caller.id])
        request = self.api_request_factory.get(url)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=caller)
        view = resolve(url)
        response = view.func(request, pk=caller.id)
        response.render()
        import pdb; pdb.set_trace()
        # results = response.data['results']

    def test_get_token_for_user_without_token(self):
        pass


# class TahoeApiKeyPostTest(TestCase):
#     def setUp(self):
#         super(TokenApiKeyPostTest, self).setUp()

#     def test_create_apik_key(self):
#         pass

#     def test_revoke_api_key(self):
#         pass

