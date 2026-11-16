from django.contrib.auth.models import AnonymousUser
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_GET

from baserow.contrib.database.views.exceptions import (
    NoAuthorizationToPubliclySharedView,
    ViewDoesNotExist,
)
from baserow.contrib.database.views.handler import ViewHandler

from .share_cards import card_for_view, draw_card


@require_GET
def share_card(request, slug):
    """
    The share card of a public view or form. Checked as an anonymous visitor, so a
    view that isn't public, or has a password, has none (404), like its public
    page (ViewHandler.get_public_view_by_slug).
    """

    try:
        view = ViewHandler().get_public_view_by_slug(AnonymousUser(), slug)
    except (ViewDoesNotExist, NoAuthorizationToPubliclySharedView) as exc:
        raise Http404 from exc

    # shortcut: drawn on every request (tens of ms); add a cache if chat apps or
    # crawlers ever fetch it often.
    response = HttpResponse(draw_card(card_for_view(view)), content_type="image/png")
    response["Cache-Control"] = "public, max-age=600"
    return response
