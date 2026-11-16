"""
The 1200x630 picture shown when a shared view or form link is posted in a chat
(og:image). One template, filled from what is shared: the design board "Share
link cards" (https://claude.ai/artifact/Hacr9YmEw1ejUSSTe9CxfZ).
"""

import io
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings

from markdown_it import MarkdownIt
from PIL import Image, ImageDraw, ImageFont, ImageOps

from baserow.contrib.database.views.handler import ViewHandler
from baserow.contrib.database.views.models import FormView
from baserow.core.storage import get_default_storage
from baserow.core.user_files.handler import UserFileHandler

ASSETS = Path(__file__).parent / "share_card_assets"
# Inter, SIL Open Font License (share_card_assets/Inter-OFL.txt), from
# github.com/google/fonts ofl/inter. shortcut: Latin, Greek and Cyrillic only;
# other scripts draw as boxes. Add a Noto font if titles use them.
FONT = ASSETS / "Inter.ttf"
# The brand plugin's logo (plugins/brand/web-frontend/.../public/img/logo.png).
BRAND_LOGO = ASSETS / "logo.png"

WIDTH, HEIGHT = 1200, 630
BAND = 120
PAD_X, PAD_TOP, PAD_BOTTOM = 64, 40, 32
COLUMN_GAP = 48
FOOTER = 24
NAVY = (42, 52, 119)
MUTED = (74, 80, 104)
PANEL = (245, 246, 250)
LINE = (228, 230, 239)
WHITE = (255, 255, 255)

FORM_QUESTIONS = 4
VIEW_COLUMNS = 3
VIEW_ROWS = 4


@dataclass
class Card:
    kind: str  # "form" or "view"
    title: str
    description: str = ""
    cover: object = None  # UserFile
    logo: object = None  # UserFile
    # (label, required); every visible question or column, in order.
    items: list = field(default_factory=list)


def markdown_to_text(content):
    """Form descriptions are markdown (FormViewDescription.vue); the card shows
    their text."""

    parts = []
    for token in MarkdownIt().parse(content or ""):
        if token.type != "inline":
            continue
        for child in token.children or []:
            if child.type in ("text", "code_inline"):
                parts.append(child.content)
            elif child.type in ("softbreak", "hardbreak"):
                parts.append(" ")
        parts.append(" ")
    return " ".join("".join(parts).split())


def card_for_view(view):
    """
    What the card shows for a public view: only what its public page shows too.
    """

    view = view.specific
    if isinstance(view, FormView):
        # The questions of the public form (PublicFormViewSerializer).
        return Card(
            kind="form",
            # Never the view's name: the public form doesn't show it (form.vue).
            title=view.title or "Form",
            description=markdown_to_text(view.description),
            cover=view.cover_image,
            logo=view.logo_image,
            items=[
                (option.name or option.field.name, option.required)
                for option in view.active_field_options
            ],
        )

    rows, _, options = ViewHandler().get_public_rows_queryset_and_field_ids(view)
    columns = [(option.field.name, False) for option in options.select_related("field")]
    count = rows.count()
    return Card(
        kind="view",
        title=view.name,
        description=(
            f"{count} {'row' if count == 1 else 'rows'} · "
            f"{len(columns)} {'column' if len(columns) == 1 else 'columns'}"
        ),
        items=columns,
    )


@lru_cache
def _font(size, weight):
    font = ImageFont.truetype(str(FONT), size)
    # Axes: optical size 14-32, weight 100-900.
    font.set_variation_by_axes([min(max(size, 14), 32), weight])
    return font


def _ellipsize(text, font, width):
    if font.getlength(text) <= width:
        return text
    while text and font.getlength(text.rstrip() + "…") > width:
        text = text[:-1]
    return text.rstrip() + "…"


def wrap(text, font, width, max_lines):
    """
    The lines of `text` that fit in `width`, at most `max_lines`; the last one
    ends in "…" when some text is left out.
    """

    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}" if line else word
        if font.getlength(candidate) <= width:
            line = candidate
            continue
        if line:
            lines.append(line)
        line = word
        # A word wider than the column is cut.
        while font.getlength(line) > width:
            cut = 1
            while cut < len(line) and font.getlength(line[: cut + 1]) <= width:
                cut += 1
            lines.append(line[:cut])
            line = line[cut:]
    if line:
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _ellipsize(lines[-1] + "…", font, width)
    return lines


def _open_image(user_file):
    if user_file is None:
        return None
    try:
        path = UserFileHandler().user_file_path(user_file)
        with get_default_storage().open(path) as file:
            image = Image.open(file)
            image.load()
        return image.convert("RGBA")
    # A missing or broken file leaves the slot to the default.
    except Exception:  # noqa: BLE001
        return None


def _text(draw, xy, text, font, fill):
    draw.text(xy, text, font=font, fill=fill, anchor="la")


def _form_panel(draw, x, y, items):
    width = 420
    label_font, more_font = _font(17, 600), _font(16, 400)
    shown, more = items[:FORM_QUESTIONS], len(items) - FORM_QUESTIONS
    inner = width - 56
    height = 24 + len(shown) * 59 + (len(shown) - 1) * 14 + 24
    if more > 0:
        height += 14 + 20
    draw.rounded_rectangle((x, y, x + width, y + height), 12, fill=PANEL)
    top = y + 24
    for label, required in shown:
        text = _ellipsize(f"{label} *" if required else label, label_font, inner)
        _text(draw, (x + 28, top), text, label_font, NAVY)
        draw.rounded_rectangle(
            (x + 28, top + 27, x + 28 + inner, top + 59), 6, fill=WHITE
        )
        top += 59 + 14
    if more > 0:
        noun = "question" if more == 1 else "questions"
        _text(draw, (x + 28, top), f"+ {more} more {noun}", more_font, MUTED)


def _view_panel(draw, x, y, items):
    width = 520
    header_font, more_font = _font(16, 600), _font(16, 400)
    shown, more = items[:VIEW_COLUMNS], len(items) - VIEW_COLUMNS
    cell = (width - 40) // VIEW_COLUMNS
    height = 20 + 42 + VIEW_ROWS * 40 + 20
    if more > 0:
        height += 12 + 20
    draw.rounded_rectangle((x, y, x + width, y + height), 12, fill=PANEL)
    left, top = x + 20, y + 20
    right = left + cell * VIEW_COLUMNS
    draw.rectangle((left, top, right, top + 42 + VIEW_ROWS * 40), fill=WHITE)
    for index, (label, _) in enumerate(shown):
        text = _ellipsize(label, header_font, cell - 24)
        _text(draw, (left + index * cell + 12, top + 12), text, header_font, NAVY)
    draw.rectangle((left, top + 40, right, top + 42), fill=LINE)
    for row in range(1, VIEW_ROWS):
        line = top + 42 + row * 40
        draw.line((left, line, right, line), fill=LINE)
    if more > 0:
        noun = "column" if more == 1 else "columns"
        bottom = top + 42 + VIEW_ROWS * 40 + 12
        _text(draw, (left, bottom), f"+ {more} more {noun}", more_font, MUTED)


def draw_card(card):
    """Returns the card as PNG bytes."""

    image = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(image)

    # Navy under the cover too, for covers with transparent parts.
    draw.rectangle((0, 0, WIDTH, BAND), fill=NAVY)
    cover = _open_image(card.cover)
    if cover is not None:
        band = ImageOps.fit(cover, (WIDTH, BAND), centering=(0.5, 0.5))
        image.paste(band, (0, 0), band)

    top = BAND + PAD_TOP
    panel_width = 0
    if card.items:
        panel_width = 420 if card.kind == "form" else 520
        panel_x = WIDTH - PAD_X - panel_width
        if card.kind == "form":
            _form_panel(draw, panel_x, top, card.items)
        else:
            _view_panel(draw, panel_x, top, card.items)
    column = WIDTH - 2 * PAD_X - (panel_width + COLUMN_GAP if panel_width else 0)

    logo = _open_image(card.logo) or Image.open(BRAND_LOGO).convert("RGBA")
    logo.thumbnail((360, 40))
    image.paste(logo, (PAD_X, top), logo)
    y = top + logo.height + 16

    label = "FORM" if card.kind == "form" else "SHARED VIEW"
    _text(draw, (PAD_X, y), label, _font(18, 600), MUTED)
    y += 22 + 16

    title_font = _font(52, 700)
    for line in wrap(card.title, title_font, column, 2):
        _text(draw, (PAD_X, y), line, title_font, NAVY)
        y += 57
    y += 16 - 5

    description_font = _font(22, 400)
    for line in wrap(card.description, description_font, column, 3):
        _text(draw, (PAD_X, y), line, description_font, MUTED)
        y += 31

    footer_y = HEIGHT - PAD_BOTTOM - FOOTER
    footer_font = _font(20, 600)
    _text(draw, (PAD_X, footer_y), settings.BRAND_NAME, footer_font, NAVY)
    host = urlparse(settings.PUBLIC_WEB_FRONTEND_URL).hostname or ""
    host_font = _font(20, 400)
    _text(
        draw,
        (WIDTH - PAD_X - host_font.getlength(host), footer_y),
        host,
        host_font,
        MUTED,
    )

    out = io.BytesIO()
    image.save(out, "PNG", optimize=True)
    return out.getvalue()
