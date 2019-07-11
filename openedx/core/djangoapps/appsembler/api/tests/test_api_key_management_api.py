
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

import ddt

from rest_framework.authtoken.models import Token

from openedx.core.djangoapps.site_configuration.tests.factories import (
    SiteFactory,
)

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

    def do_get(self, url, query_params):
        request = APIRequestFactory().get(url)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)
        view = resolve(url).func

@ddt.ddt
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.TahoeApiKeyViewSet.throttle_classes', [])
class TahoeApiKeyGetTest(TahoeApiBaseViewTest):

    def setUp(self):
        super(TahoeApiGetTest, self).setUp()
        self.
    def test_get_all_tokens(self):
        pass

    def test_get_token_for_logged_in_user(self):
        pass

    def test_get_token_for_user_without_token(self):
        pass


class TahoeApiPostTest(TestCase):
    def setUp(self):
        super(TokenApiPostTest, self).setUp()

    def test_create_apik_key(self):
        pass

    def test_revoke_api_key(self):
        pass

