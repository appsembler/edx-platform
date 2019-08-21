import os
import json

from path import path

SERVICE_VARIANT = os.environ.get('SERVICE_VARIANT', None)
CONFIG_ROOT = path('/edx/app/edxapp/')  # don't hardcode this in the future
CONFIG_PREFIX = SERVICE_VARIANT + "." if SERVICE_VARIANT else ""
with open(CONFIG_ROOT / CONFIG_PREFIX + 'env.json') as env_file:
    ENV_TOKENS = json.load(env_file)

APPSEMBLER_FEATURES = ENV_TOKENS.get('APPSEMBLER_FEATURES', {})
