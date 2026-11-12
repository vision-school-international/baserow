import os


def setup(settings):
    """
    Called by baserow.config.settings.base for every installed plugin, after the
    built-in plugins, so values set here win.
    """

    settings.INTERCP_OIDC_ISSUER = os.getenv("INTERCP_OIDC_ISSUER", "")
    settings.INTERCP_OIDC_CLIENT_ID = os.getenv("INTERCP_OIDC_CLIENT_ID", "")
    settings.INTERCP_OIDC_CLIENT_SECRET = os.getenv("INTERCP_OIDC_CLIENT_SECRET", "")
    settings.INTERCP_OIDC_NAME = os.getenv("INTERCP_OIDC_NAME", "InterCP")

    # InterCP is the only way to authenticate, so an account that predates it (e.g.
    # created with a password) must be able to link to it by its verified email.
    # Core reads this setting in AuthProviderType.get_user_and_sign_in.
    settings.BASEROW_ALLOW_MULTIPLE_SSO_PROVIDERS_FOR_SAME_ACCOUNT = True
