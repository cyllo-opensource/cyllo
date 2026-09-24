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

from odoo import fields, models, tools


class Website(models.Model):
    """Inheriting the website model to update the favicon"""
    _inherit = 'website'

    def _default_favicon(self):
        """Setting the favicon"""
        with tools.file_open('cyllo_website/static/img/cyllo-favicon.ico', 'rb') as f:
            return base64.b64encode(f.read())

    favicon = fields.Binary(
        string="Website Favicon",
        default=_default_favicon,
        help="This field holds the image used to display a favicon on the website.")
