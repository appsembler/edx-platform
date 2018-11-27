
# Getting started with the Tahoe API

This is initially a "quick-n-dirty" doc

## Set up / Prerequisites

For devstack, the environment needs to be set up for multiple sites.

* Create a custom site
* Cerate an Organization mapping for the site
* Create a SiteConfiguration
* Make sure the SiteConfiguration has 'course_org_filter' as one of the JSON
  data values and that the value is the same as the short name for the Organization


## Authentication

the Tahoe API uses token authentication.

A token is mapped to a specific user. Therefore to access the registration api,
a token needs to be created for the user


How to create a token,

use the api management command, `tahoe_create_token <username>` to create or
get the token for the user


Here is an example script to call the registration API:

```
#!/usr/bin/env python
"""
This is a quickly hacked together script to test the registration api


To use this script to test the Tahoe registration API, you'll need to

1. Enable multiple sites and create a SiteConfiguration object for the site
   for which you are running this script
2. Create an AMC admin user token
3. Set the token to the "TAHOE_API_USER_KEY" environment variable
4. Set the host to the one in your dev environment in this script

For "2", you can use the Tahoe registration API management command,
"tahoe_create_token"

"""

import os
import pprint
import requests

import faker
import random

FAKE = faker.Faker()


host = 'http://alpha.localhost:8000'
api_url_root = host + '/tahoe/api/v1/'
reg_api_url = api_url_root + 'registrations/'


def generate_user_info():
    return dict(
        name=FAKE.name(),
        username=FAKE.user_name(),
        email=FAKE.email(),
        password=FAKE.password()
    )

def register_user(data):

    print('calling url:{} with data:'.format(reg_api_url))
    pprint.pprint(data)

    my_token = os.environ.get('TAHOE_API_USER_KEY')

    response = requests.post(
        reg_api_url,
        headers={'Authorization': 'Token {}'.format(my_token)},
        data=data)

    return response.json()


def main():
    # reg_data = dict(
    #     name='El Mo',
    #     username='elmo',
    #     email='elmo@example.com',
    #     password='bad-password',
    #     )

    reg_data = generate_user_info()

    print('Registering user:')
    pprint.pprint(reg_data)

    print('making call...')
    response_data = register_user(reg_data)
    print('response data:')
    pprint.pprint(response_data)


if __name__ == '__main__':
    main()

```
