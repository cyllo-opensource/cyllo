# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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


class HelpDeskStage(models.Model):
    _name = "helpdesk.stage"
    _description = "HelpDesk Stage"

    name = fields.Char(string="Stage", ondelete='restrict',
                       help="Add more stages")
    sequence = fields.Integer(string="Sequence", default=1,
                              help="Order of stage")
    is_closed = fields.Boolean(string="Is Closed Stage", help="Tick if it is closed stage")
    fold = fields.Boolean(string="Fold", help="Stage folded in kanban")
    template_id = fields.Many2one('mail.template', string='Email Template', help="Automated email sent to the customer when the ticket reaches this stage.")
