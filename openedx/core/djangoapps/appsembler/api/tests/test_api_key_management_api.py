
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

    def create_get_request(self, url, query_params):
        request = self.api_request_factory.get(url)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)
        view = resolve(url).func

@ddt.ddt
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.TahoeApiKeyViewSet.throttle_classes', [])
class TahoeApiKeyGetTest(TahoeApiBaseViewTest):

    def setUp(self):
        super(TahoeApiKeyGetTest, self).setUp()

        self.my_site_users = [UserFactory() for i in range(3)]
        for user in self.my_site_users:
            UserOrganizationMappingFactory(user=user,
                                           organization=self.my_site_org)

        self.other_site_users = [UserFactory()]
        for user in self.other_site_users:
            UserOrganizationMappingFactory(user=user,
                                           organization=self.other_site_org)

    def test_get_all_tokens(self):
        url = reverse('tahoe-api:v1:api-keys-list')
        request = self.api_request_factory.get(url)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)
        view = resolve(url).func

    def test_get_token_for_logged_in_user(self):
        pass

    def test_get_token_for_user_without_token(self):
        pass


# class TahoeApiKeyPostTest(TestCase):
#     def setUp(self):
#         super(TokenApiKeyPostTest, self).setUp()

#     def test_create_apik_key(self):
#         pass

#     def test_revoke_api_key(self):
#         pass

