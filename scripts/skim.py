"""
A Python script to skim po files based on a base POFile (or a URL)
"""
import os
import polib


def skim(open_edx_release_file, theme_file, custom_file):
    """
    Remove entries from `dest` that exists in `base`.

    Useful to make it cut Translation time by removing entries that is in the Open edX translation files.

    :param open_edx_release_file: The path to the Open edX release file e.g. release-ficus.po
    :param theme_file: The path to the theme po file e.g. theme.po
    :return:
    """

    script_dirname = os.path.dirname(__file__)
    english_dir = script_dirname, '../conf/locale/en/LC_MESSAGES'

    base_po = polib.pofile(os.path.join(script_dirname, 'open-edx-releases', open_edx_release_file))
    dest_po = polib.pofile(os.path.join(english_dir, theme_file))

    for entry in reversed(dest_po):
        if entry in base_po:
            dest_po.remove(entry)

    dest_po.save(fpath=os.path.join(english_dir, custom_file))


skim('release-ficus.po', 'django.po', 'custom.po')
# skim('release-ficus-js.po', 'djangojs.po', 'customjs.po')
