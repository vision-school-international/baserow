from baserow.core.auth_provider.models import AuthProviderModel


class InterCPAuthProviderModel(AuthProviderModel):
    """
    The single InterCP provider row. It holds no configuration: the issuer, client id
    and secret come from settings, so they never live in the database.
    """
