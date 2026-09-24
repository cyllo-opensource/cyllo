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


class ResConfigSettings(models.TransientModel):
    """
       Extends the base 'res.config.settings' model to include
       additional configuration settings related to timesheet durations
       and rounding.
   """
    _inherit = 'res.config.settings'

    minimal_duration = fields.Integer(
        help="Field to set the minimum timesheet duration", default=15,
        config_parameter="cyllo_timesheet_grid.minimal_duration")
    round_up = fields.Integer(help="Field to set the rounding time", default=15,
                              config_parameter="cyllo_timesheet_grid.round_up")
