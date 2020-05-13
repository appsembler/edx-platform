"""
Exception classes for credential_criteria Django app.'
"""


class CredentialCriteriaException(Exception):
    """
    Custom exception class to catch various errors with credential criterion/criteria.
    """
    def __init__(self, msg='', user=None):
        msg = "Could not calculate satisfaction of credential criteria for {}.  Errors were {}".format(
            user.username, msg
        )
        super(CredentialCriteriaException, self).__init__(msg)
