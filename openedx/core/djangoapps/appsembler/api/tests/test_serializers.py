
import ddt
from dateutil.parser import parse

from django.test import TestCase

# from rest_framework.authtoken.models import Token

from student.tests.factories import UserFactory

from openedx.core.djangoapps.site_configuration.tests.factories import (
    SiteFactory,
)

from openedx.core.djangoapps.appsembler.api.v1.serializers import (
    TahoeApiKeyDetailSerializer,
    TahoeApiKeyListSerializer,
)

from openedx.core.djangoapps.appsembler.api.tests.factories import (
    TokenFactory,
    OrganizationFactory,
    UserOrganizationMappingFactory,
)


@ddt.ddt
class TahoeApiKeyDetailSerializerTest(TestCase):

    def setUp(self):
        self.my_site = SiteFactory(domain='my-site.test')
        self.other_site = SiteFactory(domain='other-site.test')
        self.other_site_org = OrganizationFactory(sites=[self.other_site])
        self.my_site_org = OrganizationFactory(sites=[self.my_site])
        self.my_site_users = [UserOrganizationMappingFactory(
            organization=self.my_site_org).user for i in xrange(5)]

        self.my_tokens = [TokenFactory(user=self.my_site_users[0]),
                          TokenFactory(user=self.my_site_users[2])]

    def test_instantiate_one_with_token(self):
        
        token = self.my_tokens[0]

        obj = dict(
            user_id=token.user.id,
            username=token.user.username,
            created=token.created,
            secret=token.key 
        )
        serializer = TahoeApiKeyDetailSerializer(instance=obj)
        assert serializer.data['user_id'] == token.user.id
        assert serializer.data['username'] == token.user.username
        assert serializer.data['secret'] == token.key
        assert parse(serializer.data['created']) == token.created

    def test_instance_one_without_token(self):
        user = UserOrganizationMappingFactory(organization=self.my_site_org).user
        obj = dict(
            user_id=user.id,
            username=user.username,
        )
        serializer = TahoeApiKeyDetailSerializer(instance=obj)
        assert serializer.data['user_id'] == user.id
        assert serializer.data['username'] == user.username
        assert not serializer.data.has_key('secret')
        assert not serializer.data.has_key('created')


@ddt.ddt
class TahoeApiKeyListSerializerTest(TestCase):

    def setUp(self):
        self.my_site = SiteFactory(domain='my-site.test')
        self.other_site = SiteFactory(domain='other-site.test')
        self.other_site_org = OrganizationFactory(sites=[self.other_site])
        self.my_site_org = OrganizationFactory(sites=[self.my_site])

    def test_single_instance_with_token_and_admin_privilege(self):
        """

        """
        uom = UserOrganizationMappingFactory(organization=self.my_site_org,
                                             is_amc_admin=True)
        token = TokenFactory(user=uom.user)

        assert uom.user.auth_token == token

        serializer = TahoeApiKeyListSerializer(instance=uom.user,
                                               context=dict(site=self.my_site))
        data = serializer.data
        assert set(data.keys()) == set(['user_id', 'username', 'token_created'])
        assert data['user_id'] == uom.user.id
        assert data['username'] == uom.user.username
        assert parse(data['token_created']) == token.created

    def test_single_instance_admin_without_token(self):
        pass

    def test_many(self):
        """
        Make sure we haven't broken how DRF handles  multiple instance'
        """
        pass
