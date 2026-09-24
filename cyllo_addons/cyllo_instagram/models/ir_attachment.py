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
from odoo import fields, models


class IrAttachment(models.Model):
    """
        Extends the base ir.attachment model to add a field for storing
        Instagram public URLs for attachments.
    """
    _inherit = "ir.attachment"

    public_url = fields.Char(string="Url", compute="_compute_public_url", help="Url for the attachment")

    def _compute_public_url(self):
        """
        Computes the Instagram public URL for each attachment record.
        """
        for attachment in self:
            attachment.public_url = '%s/web/content/%s' % (attachment.get_base_url(), attachment.id)
