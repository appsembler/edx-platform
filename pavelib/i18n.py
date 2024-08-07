"""
Internationalization tasks
"""


import re
import subprocess
import sys

from path import Path as path
from paver.easy import cmdopts, needs, sh, task
from six.moves import input

from .utils.cmd import django_cmd
from .utils.envs import Env
from .utils.timer import timed

try:
    from pygments.console import colorize
except ImportError:
    colorize = lambda color, text: text

DEFAULT_SETTINGS = Env.DEVSTACK_SETTINGS


@task
@needs(
    "pavelib.prereqs.install_prereqs",
    "pavelib.i18n.i18n_validate_gettext",
)
@cmdopts([
    ("verbose", "v", "Sets 'verbose' to True"),
])
@timed
def i18n_extract(options):
    """
    Extract localizable strings from sources
    """
    verbose = getattr(options, "verbose", None)
    cmd = "i18n_tool extract"

    if verbose:
        cmd += " -v"

    sh(cmd)


@task
@timed
def i18n_fastgenerate():
    """
    Compile localizable strings from sources without re-extracting strings first.
    """
    sh("i18n_tool generate")


@task
@needs("pavelib.i18n.i18n_extract")
@timed
def i18n_generate():
    """
    Compile localizable strings from sources, extracting strings first.
    """
    sh("i18n_tool generate")


@task
@needs("pavelib.i18n.i18n_extract")
@timed
def i18n_generate_strict():
    """
    Compile localizable strings from sources, extracting strings first.
    Complains if files are missing.
    """
    sh("i18n_tool generate --strict")


@task
@needs("pavelib.i18n.i18n_extract")
@timed
def i18n_dummy():
    """
    Simulate international translation by generating dummy strings
    corresponding to source strings.
    """
    sh("i18n_tool dummy")
    # Need to then compile the new dummy strings
    sh("i18n_tool generate")


@task
@needs(
    "pavelib.prereqs.install_prereqs",
)
@timed
def i18n_compilejs(options):
    """
    Generating djangojs.js files using django-statici18n
    """
    settings = 'devstack_docker'

    # Generate static i18n JS files.
    for system in ['lms', 'cms']:
        sh(django_cmd(system, settings, 'compilejsi18n'))


@task
@timed
def i18n_validate_gettext():
    """
    Make sure GNU gettext utilities are available
    """

    returncode = subprocess.call(['which', 'xgettext'])

    if returncode != 0:
        msg = colorize(
            'red',
            "Cannot locate GNU gettext utilities, which are "
            "required by django for internationalization.\n (see "
            "https://docs.djangoproject.com/en/dev/topics/i18n/"
            "translation/#message-files)\nTry downloading them from "
            "http://www.gnu.org/software/gettext/ \n"
        )

        sys.stderr.write(msg)
        sys.exit(1)


@task
@timed
def i18n_validate_transifex_config():
    """
    Make sure config file with username/password exists
    """
    home = path('~').expanduser()
    config = home / '.transifexrc'

    if not config.isfile or config.getsize == 0:
        msg = colorize(
            'red',
            u"Cannot connect to Transifex, config file is missing"
            u" or empty: {config} \nSee "
            u"http://help.transifex.com/features/client/#transifexrc \n".format(
                config=config,
            )
        )

        sys.stderr.write(msg)
        sys.exit(1)


@task
@needs("pavelib.i18n.i18n_validate_transifex_config")
@timed
def i18n_transifex_push():
    """
    Push source strings to Transifex for translation
    """
    sh("i18n_tool transifex push")


@task
@needs("pavelib.i18n.i18n_validate_transifex_config")
@timed
def i18n_transifex_pull():
    """
    Pull translated strings from Transifex
    """
    sh("i18n_tool transifex pull")


@task
@timed
def i18n_rtl():
    """
    Pull all RTL translations (reviewed AND unreviewed) from Transifex
    """
    sh("i18n_tool transifex rtl")

    print("Now generating langugage files...")

    sh("i18n_tool generate --rtl")

    print("Committing translations...")
    sh('git clean -fdX conf/locale')
    sh('git add conf/locale')
    sh('git commit --amend')


@task
@timed
def i18n_ltr():
    """
    Pull all LTR translations (reviewed AND unreviewed) from Transifex
    """
    sh("i18n_tool transifex ltr")

    print("Now generating langugage files...")

    sh("i18n_tool generate --ltr")

    print("Committing translations...")
    sh('git clean -fdX conf/locale')
    sh('git add conf/locale')
    sh('git commit --amend')


@task
@needs(
    "pavelib.i18n.i18n_release_pull_and_compile",
    "pavelib.i18n.i18n_clean",
    "pavelib.i18n.i18n_transifex_pull",
    "pavelib.i18n.i18n_extract",
    "pavelib.i18n.i18n_dummy",
    "pavelib.i18n.i18n_generate_strict",
)
@timed
def i18n_robot_pull_edx():
    """
    Pull source strings, generate po and mo files, and validate
    """
    raise Exception('Appsembler: Using `i18n_robot_pull` instead.')

    # sh('paver test_i18n')
    # Tests were removed from repo, but there should still be tests covering the translations
    # TODO: Validate the recently pulled translations, and give a bail option
    sh('git clean -fdX conf/locale/rtl')
    sh('git clean -fdX conf/locale/eo')
    print("\n\nValidating translations with `i18n_tool validate`...")
    sh("i18n_tool validate")

    con = input("Continue with committing these translations (y/n)? ")

    if con.lower() == 'y':
        sh('git add conf/locale')
        sh('git add cms/static/js/i18n')
        sh('git add lms/static/js/i18n')

        sh(
            'git commit --message='
            '"Update translations (autogenerated message)" --edit'
        )


@task
@timed
def i18n_clean():
    """
    Clean the i18n directory of artifacts
    """
    sh('git clean -fdX conf/locale')


@task
@needs(
    "pavelib.i18n.i18n_clean",
    "pavelib.i18n.i18n_extract",
    "pavelib.i18n.i18n_transifex_push",
)
@timed
def i18n_robot_push():
    """
    Extract new strings, and push to transifex
    """
    pass


@task
@needs(
    "pavelib.i18n.i18n_validate_transifex_config",
    "pavelib.i18n.i18n_generate",
)
@timed
def i18n_release_push():
    """
    Push release-specific resources to Transifex.
    """
    resources = find_release_resources()
    sh("i18n_tool transifex push " + " ".join(resources))


@task
@needs(
    "pavelib.i18n.i18n_validate_transifex_config",
)
@timed
def i18n_release_pull():
    """
    Pull release-specific translations from Transifex.
    """
    resources = find_release_resources()
    sh("i18n_tool transifex pull " + " ".join(resources))


@task
@needs(
    "pavelib.i18n.i18n_clean",
)
def tahoe_i18n_transifex_release_pull(require_reviewed=False):
    """
    Pull Tahoe release translation files: adapted from `i18n.transifex.pull`.

    Adapted from the edX repo edx/i18n-tools package, this helper allows to pull either reviewed or unreviewed
    entries. This taks should be removed when https://github.com/edx/i18n-tools/issues/96 is resolved.
    """
    # Keeping imports locally for an easy revert.
    from i18n import config
    from i18n.execute import execute
    from i18n.transifex import clean_translated_locales

    i18n_configs = config.Configuration()  # Read the `locale/config.yaml`
    resources = find_release_resources()

    for locale in i18n_configs.translated_locales:
        cmd = u'tx pull --force --mode={mode} --minimum-perc=3 -l {locale}'.format(
            locale=locale,
            mode='reviewed' if require_reviewed else 'onlytranslated'
        )
        if resources:
            for resource in resources:
                execute(cmd + ' -r {resource}'.format(resource=resource))
        else:
            execute(cmd)
    clean_translated_locales(i18n_configs)


@task
@needs(
    "pavelib.i18n.i18n_clean",
)
@cmdopts([
    ("settings=", "s", "The settings to use (defaults to devstack)"),
])
@timed
def i18n_robot_pull(options):
    """
    Pull release-specific translations from Transifex, generate po and mo files, and validate.

    Appsembler: This is what we use for Tahoe.
    """
    settings = options.get('settings', DEFAULT_SETTINGS)

    sh('git clean -fdX conf/locale/rtl')
    sh('git clean -fdX conf/locale/eo')
    print("\n\nValidating translations with `i18n_tool validate`...")

    tahoe_i18n_transifex_release_pull()

    sh("i18n_tool validate")
    sh("i18n_tool generate")

    # Generate static i18n JS files.
    for system in ['lms', 'cms']:
        sh(django_cmd(system, settings, 'compilejsi18n'))

    con = input("Continue with committing these translations (y/n)? ")
    if con.lower() == 'y':
        sh('git add conf/locale')
        sh('git add cms/static/js/i18n')
        sh('git add lms/static/js/i18n')

        sh(
            'git commit --message='
            '"Update translations (autogenerated message)" --edit'
        )


def find_release_resources():
    """
    Validate the .tx/config file for release files, returning the resource names.

    For working with release files, the .tx/config file should have exactly
    two resources defined named "release-*".  Check that this is true.  If
    there's a problem, print messages about it.

    Returns a list of resource names, or raises ValueError if .tx/config
    doesn't have two resources.

    """
    # An entry in .tx/config for a release will look like this:
    #
    #    [edx-platform.release-dogwood]
    #    file_filter = conf/locale/<lang>/LC_MESSAGES/django.po
    #    source_file = conf/locale/en/LC_MESSAGES/django.po
    #    source_lang = en
    #    type = PO
    #
    #    [edx-platform.release-dogwood-js]
    #    file_filter = conf/locale/<lang>/LC_MESSAGES/djangojs.po
    #    source_file = conf/locale/en/LC_MESSAGES/djangojs.po
    #    source_lang = en
    #    type = PO

    rx_release = r"^\[([\w-]+\.release-[\w-]+)\]$"
    with open(".tx/config") as tx_config:
        resources = re.findall(rx_release, tx_config.read(), re.MULTILINE)

    if len(resources) == 2:
        return resources

    if not resources:
        raise ValueError("You need two release-* resources defined to use this command.")
    else:
        msg = "Strange Transifex config! Found these release-* resources:\n" + "\n".join(resources)
        raise ValueError(msg)
