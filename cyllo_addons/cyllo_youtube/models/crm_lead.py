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


class CrmLead(models.Model):
    """
    Inherits the base crm.lead model and adds Tasks information in
    the lead form.
    """
    _inherit = 'crm.lead'

    unique_yt_comment_number = fields.Char(string='Unique YouTube Comment Id',
                                           help="Unique identifier for the lead on YouTube.")
    youtube_user_number = fields.Char(string='Unique YouTube Id',
                                      help="Unique identifier for the partner on YouTube.")
