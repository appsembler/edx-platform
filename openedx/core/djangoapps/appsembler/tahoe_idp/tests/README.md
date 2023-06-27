Tests which rely on ENABLE_TAHOE_IDP: True and which cause a User or UserProfile to be saved
will need to also use:
    @override_settings(TAHOE_IDP_CONFIGS={'API_KEY':'fake', 'BASE_URL': 'http://localhost'})
    (or in a context manager)
due to the post_save Signal receivers in tahoe-idp package.
