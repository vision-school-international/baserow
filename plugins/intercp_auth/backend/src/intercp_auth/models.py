from django.conf import settings
from django.db import models

from baserow.core.auth_provider.models import AuthProviderModel


class InterCPAuthProviderModel(AuthProviderModel):
    """
    The single InterCP provider row. It holds no configuration: the issuer, client id
    and secret come from settings, so they never live in the database.
    """


class DefaultWorkspaceJoin(models.Model):
    """
    A user was put in the default workspace once. Recorded so that a staff member
    can remove them: they're not added again on the next sign-in or startup. Same
    user/workspace pair as core's WorkspaceUser (core/models.py:468-491).
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    workspace = models.ForeignKey("core.Workspace", on_delete=models.CASCADE)

    class Meta:
        unique_together = [["user", "workspace"]]
