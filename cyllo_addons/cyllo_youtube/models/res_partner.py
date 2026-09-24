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
from odoo import _, fields, models


class ResPartner(models.Model):
    """
    Inherits the base res.partner model and adds Tasks information in
    the partner form.
    """
    _inherit = 'res.partner'

    post_id = fields.Many2one('social.media.post', string='Related Post',
                              help="The post where this contact was created.")
    unique_yt_number = fields.Char(string='Feed',
                                   help="Unique identifier for the partner's feed on YouTube.")
    youtube_account_id = fields.Many2one('youtube.account',
                                         string='Related Youtube Account',
                                         help="Account related to partner")
