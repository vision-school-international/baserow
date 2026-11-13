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
    # Every user joins this workspace once: on their first InterCP sign-in or, for
    # existing users, on startup. Empty turns it off.
    # base.py only catches ImportError around setup(), so a bad value must not
    # raise: it would stop the whole backend from starting.
    default_workspace_id = os.getenv("INTERCP_DEFAULT_WORKSPACE_ID", "").strip()
    try:
        settings.INTERCP_DEFAULT_WORKSPACE_ID = int(default_workspace_id or 0) or None
    except ValueError:
        print(
            "intercp_auth: INTERCP_DEFAULT_WORKSPACE_ID must be a workspace ID, got "
            f"{default_workspace_id!r}. No default workspace is used."
        )
        settings.INTERCP_DEFAULT_WORKSPACE_ID = None

    # InterCP is the only way to authenticate, so an account that predates it (e.g.
    # created with a password) must be able to link to it by its verified email.
    # Core reads this setting in AuthProviderType.get_user_and_sign_in.
    settings.BASEROW_ALLOW_MULTIPLE_SSO_PROVIDERS_FOR_SAME_ACCOUNT = True
