"""
Test the i18n module helpers.
"""
import unittest
from django.conf import settings

from openedx.core.djangoapps.appsembler.i18n.helpers import xblock_translate


@unittest.skipIf(
    settings.TAHOE_NUTMEG_TEMP_SKIP_TEST,
    'Fix i18n related tests later'
)
def test_xblock_translate():
    translated_text = xblock_translate('drag-and-drop-v2', 'eo', 'The Top Zone')
    assert 'Töp' in translated_text
