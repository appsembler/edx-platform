
import ddt
from dateutil.parser import parse

from django.test import TestCase

from student.tests.factories import UserFactory

from openedx.core.djangoapps.appsembler.api.v1.serializers import (
    TahoeApiKeyDetailSerializer,
)

from openedx.core.djangoapps.appsembler.api.tests.factories import (
    TokenFactory,
)


@ddt.ddt
class TahoeApiKeyDetailSerializerTest(TestCase):

    def setUp(self):
        self.users = [UserFactory() for i in xrange(2)]

    def test_instantiate_one_with_token(self):
        the_user = self.users[0]
        token = TokenFactory(user=the_user)
        obj = dict(
            user_id=the_user.id,
            username=the_user.username,
            created=token.created,
            secret=token.key 
        )
        serializer = TahoeApiKeyDetailSerializer(instance=obj)
        assert serializer.data['user_id'] == token.user.id
        assert serializer.data['username'] == the_user.username
        assert serializer.data['secret'] == token.key
        assert parse(serializer.data['created']) == token.created

    def test_instance_one_without_token(self):
        the_user = self.users[0]
        obj = dict(
            user_id=the_user.id,
            username=the_user.username,
        )
        serializer = TahoeApiKeyDetailSerializer(instance=obj)
        assert serializer.data['user_id'] == the_user.id
        assert serializer.data['username'] == the_user.username
        assert not serializer.data.has_key('secret')
        assert not serializer.data.has_key('created')
