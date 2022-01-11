"""
Helpers for the theme sass storage manager.
"""

import beeline
import json

import cssutils
import os
import sass

from django.core.files.storage import get_storage_class
from django.conf import settings
from django.contrib.sites.models import Site

from openedx.core.djangoapps.theming.models import SiteTheme
from openedx.core.djangoapps.theming.helpers import get_theme_base_dir, Theme


@beeline.traced(name="get_customer_files_storage")
def get_customer_files_storage():
    kwargs = {}
    # Passing these settings to the FileSystemStorage causes an exception
    # TODO: Use settings instead of hardcoded in Python
    if not settings.DEBUG:
        kwargs = {
            'location': 'customer_files',
            'file_overwrite': False
        }

    return get_storage_class()(**kwargs)


@beeline.traced(name="get_initial_sass_variables")
def get_initial_sass_variables():
    """
    This method loads the SASS variables file from the currently active theme. It is used as a default value
    for the sass_variables field on new Microsite objects.
    """
    values = get_branding_values_from_file()
    labels = get_branding_labels_from_file()
    return [(val[0], (val[1], lab[1])) for val, lab in zip(values, labels)]


@beeline.traced(name="get_branding_values_from_file")
def get_branding_values_from_file():
    if not settings.ENABLE_COMPREHENSIVE_THEMING:
        return {}

    try:
        default_site = Site.objects.get(id=settings.SITE_ID)
    except Site.DoesNotExist:
        # Empty values dictionary if the database isn't initialized yet.
        # This unblocks migrations and other cases before having a default site.
        return {}

    site_theme = SiteTheme(site=default_site, theme_dir_name=settings.DEFAULT_SITE_THEME)
    theme = Theme(
        name=site_theme.theme_dir_name,
        theme_dir_name=site_theme.theme_dir_name,
        themes_base_dir=get_theme_base_dir(site_theme.theme_dir_name),
        project_root=settings.PROJECT_ROOT,
    )
    if theme:
        sass_var_file = os.path.join(theme.customer_specific_path, 'static',
                                     'sass', 'base', '_branding-basics.scss')
        with open(sass_var_file, 'r') as f:
            contents = f.read()
            values = sass_to_dict(contents)
    else:
        values = {}
    return values


@beeline.traced(name="get_branding_labels_from_file")
def get_branding_labels_from_file(custom_branding=None):
    if not settings.ENABLE_COMPREHENSIVE_THEMING:
        return []

    css_output = compile_sass('_brand.scss', custom_branding)
    css_rules = cssutils.parseString(css_output, validate=False).cssRules
    labels = []
    for rule in css_rules:
        # we don't want comments in the final output
        if rule.typeString == "COMMENT":
            continue
        var_name = rule.selectorText.replace('.', '$')
        value = rule.style.content
        labels.append((var_name, value))
    return labels


@beeline.traced(name="compile_sass")
def compile_sass(sass_file, custom_branding=None):
    from openedx.core.djangoapps.theming.helpers import get_theme_base_dir, Theme
    try:
        default_site = Site.objects.get(id=settings.SITE_ID)
    except Site.DoesNotExist:
        # Empty CSS output if the database isn't initialized yet.
        # This unblocks migrations and other cases before having a default site.
        return ''

    site_theme = SiteTheme(site=default_site, theme_dir_name=settings.DEFAULT_SITE_THEME)
    theme = Theme(
        name=site_theme.theme_dir_name,
        theme_dir_name=site_theme.theme_dir_name,
        themes_base_dir=get_theme_base_dir(site_theme.theme_dir_name),
        project_root=settings.PROJECT_ROOT,
    )
    sass_var_file = os.path.join(theme.path, 'static', 'sass', sass_file)
    customer_specific_includes = os.path.join(theme.customer_specific_path, 'static', 'sass')
    importers = None
    if custom_branding:
        importers = [(0, custom_branding)]
    css_output = sass.compile(
        filename=sass_var_file,
        include_paths=[customer_specific_includes],
        importers=importers
    )
    return css_output


def sass_to_dict(sass_input):
    sass_vars = []
    lines = (line for line in sass_input.splitlines() if line and not line.startswith('//'))
    for line in lines:
        key, val = line.split(':')
        val = val.split('//')[0]
        val = val.strip().replace(";", "")
        sass_vars.append((key, val))
    return sass_vars


def sass_to_json_string(sass_input):
    sass_dict = sass_to_dict(sass_input)
    return json.dumps(sass_dict, sort_keys=True, indent=2)
