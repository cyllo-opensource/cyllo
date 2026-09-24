# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import base64
import io
import logging

from PIL import Image, WebPImagePlugin  # noqa: F401 (registers the WebP codec - PIL's lazy plugin discovery misses it in some environments)

from odoo import models

_logger = logging.getLogger(__name__)

SOCIAL_SAFE_IMAGE_MIMETYPES = ('image/jpeg', 'image/png')


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def get_social_safe_image(self):
        """Returns self if already a jpeg/png (what Facebook/Instagram's
        Graph API can fetch and decode), otherwise a cached PNG conversion
        of this attachment (webp, bmp, gif, ...) so uploads in those formats
        still get posted instead of silently skipped. False if this isn't
        an image or fails to decode."""
        self.ensure_one()
        if not (self.mimetype or '').startswith('image/'):
            return False
        if self.mimetype in SOCIAL_SAFE_IMAGE_MIMETYPES:
            return self
        Attachment = self.sudo()
        converted = Attachment.search([
            ('res_model', '=', 'ir.attachment'),
            ('res_id', '=', self.id),
            ('name', '=', 'converted.png'),
        ], limit=1)
        if converted:
            return converted
        try:
            image = Image.open(io.BytesIO(base64.b64decode(self.datas)))
            buffer = io.BytesIO()
            image.convert('RGBA').save(buffer, format='PNG')
            return Attachment.create({
                'name': 'converted.png',
                'datas': base64.b64encode(buffer.getvalue()),
                'mimetype': 'image/png',
                'res_model': 'ir.attachment',
                'res_id': self.id,
                'public': True,
            })
        except Exception:
            _logger.exception("Failed to convert attachment %s to a social-media-safe PNG", self.id)
            return False
