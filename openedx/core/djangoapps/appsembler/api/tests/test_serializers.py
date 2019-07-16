
import ddt
from dateutil.parser import parse

from django.test import TestCase

from student.tests.factories import UserFactory

from openedx.core.djangoapps.appsembler.api.v1.serializers import (
    TahoeApiKeyDetailSerializer,
    TahoeApiKeyListSerializer,
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


@ddt.ddt
class TahoeApiKeyListSerializerTest(TestCase):

    def setUp(self):
        pass

    def test_single_instance(self):
        """
        Simple check with a single user and all the fields available
        """
        the_user = UserFactory()
        obj = dict(
            user_id=the_user.id,
            username=the_user.username,
        )
        serializer = TahoeApiKeyListSerializer(instance=obj)
        assert serializer.data['user_id'] == the_user.id
        assert serializer.data['username'] == the_user.username

    def test_multiple_instances(self):
        user_count = 5
        token_count = 3
        users = [UserFactory() for i in xrange(user_count)]
        tokens = [TokenFactory(user=users[i]) for i in xrange(token_count)]
        data = []
        for i, user in enumerate(users):
            rec = dict(
                user_id=user.id,
                username=user.username,
            )
            if i < token_count:
                rec['created'] = tokens[i].created
            data.append(rec)

        serializer = TahoeApiKeyListSerializer(instance=data, many=True)
        for i, rec in enumerate(serializer.data):
            assert rec['user_id'] == users[i].id
            assert rec['username'] == users[i].username
            if i < token_count:
                assert parse(rec['created']) ==  tokens[i].created
