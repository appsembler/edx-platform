"""Tests for the lms module itself."""


import logging
import mimetypes

from django.conf import settings
from django.test import TestCase

from edxmako import LOOKUP, add_lookup

log = logging.getLogger(__name__)


class LmsModuleTests(TestCase):
    """
    Tests for lms module itself.
    """

    def test_new_mimetypes(self):
        extensions = ['eot', 'otf', 'ttf', 'woff']
        for extension in extensions:
            mimetype, _ = mimetypes.guess_type('test.' + extension)
            self.assertIsNotNone(mimetype)

    def test_api_docs(self):
        """
        Tests that requests to the `/api-docs/` endpoint do not raise an exception.
        """
        response = self.client.get('/api-docs/')
        self.assertFalse(settings.FEATURES.get('TAHOE_ENABLE_API_DOCS_URLS'))
        self.assertEqual(404, response.status_code)  # Tahoe: Changed from `200`
