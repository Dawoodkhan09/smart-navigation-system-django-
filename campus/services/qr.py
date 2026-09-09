"""
QR-code generation for a Location's public visitor-app URL. Pure-ish
functions matching the style of the other campus/services/ modules -
the only Django import is for building an absolute URL from the current
request, nothing ORM/view-specific lives here.
"""

import io

import qrcode
from django.urls import reverse
from qrcode.constants import ERROR_CORRECT_H


def build_location_url(request, location) -> str:
    """Full absolute URL a QR sticker encodes, e.g. https://host/l/main-gate/.

    A full URL (not a bare code) is what lets a visitor's stock phone
    camera app open it directly, with no app install needed.
    """
    path = reverse('location-qr-landing', args=[location.code])
    return request.build_absolute_uri(path)


def build_campus_url(request, campus) -> str:
    """
    Full absolute URL a CAMPUS's own QR sticker encodes, e.g.
    https://host/app/c/main-campus/. Scanning it locks the visitor's
    session to this campus (see campus.views.campus_qr_landing) and sends
    them straight into its map - they can't browse another campus's data
    afterwards without scanning a QR that belongs to it instead.
    """
    path = reverse('campus-qr-landing', args=[campus.slug])
    return request.build_absolute_uri(path)


def qr_png_bytes(url: str, *, box_size: int = 10, border: int = 2, logo_path: str | None = None) -> bytes:
    """
    Renders `url` as a PNG QR code.

    Error-correction level H (the highest level qrcode supports) is used
    deliberately - these codes go on outdoor walls and stay there for
    years, so they need to keep scanning even weathered, scuffed, or
    partly covered.
    """
    qr = qrcode.QRCode(
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white').convert('RGB')

    if logo_path:
        _paste_center_logo(image, logo_path)

    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def _paste_center_logo(image, logo_path: str) -> None:
    """Pastes a small logo in the middle of the QR code. Safe at error
    correction level H, which tolerates up to ~30% of the code being
    obscured - a centered logo at roughly a quarter of the code's width
    stays well under that."""
    from PIL import Image

    logo = Image.open(logo_path).convert('RGBA')
    image_w, image_h = image.size
    logo_size = image_w // 4
    logo.thumbnail((logo_size, logo_size))

    position = ((image_w - logo.size[0]) // 2, (image_h - logo.size[1]) // 2)
    image.paste(logo, position, logo)
