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
    """ Class to inherit res config setting and add field """
    _inherit = 'res.config.settings'

    module_cyllo_field_service_project = fields.Boolean(
        string="Project in Field Service",
        help="Enable to get features in Project")
    module_cyllo_field_service_fleet = fields.Boolean(
        string="Fleet in Field Service",
        help="Enable to get features in fleet")
    module_cyllo_field_service_equipment = fields.Boolean(
        string="Equipments in Field Service",
        help="Enable to get features in maintenance")
    deadline_reminder = fields.Integer('Deadline Reminder',
                                       help="Send a reminder a few days before the deadline.",
                                       config_parameter="cyllo_field_service.deadline_reminder",
                                       default=1)
