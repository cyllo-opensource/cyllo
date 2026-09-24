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

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PlmEcoStage(models.Model):
    _name = 'plm.eco.stage'
    _description = 'ECO Stage'
    _order = 'sequence, id'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=1,
    )
    in_progress = fields.Boolean(
        string='In Progress',
        default=False,
    )
    done = fields.Boolean(
        string='Done',
        default=False,
    )
    cancelled = fields.Boolean(
        string='Cancelled',
        default=False,
    )
    fold = fields.Boolean(
        string='Fold in Kanban',
        default=False,
    )

    @api.constrains('done')
    def _check_done_stage(self):
        """ Ensure that only one stage can be marked as 'Done' (completed) in the system. """
        for stage in self:
            if stage.done:
                other_done_stages = self.search([('done', '=', True), ('id', '!=', stage.id)])
                if other_done_stages:
                    raise ValidationError(_("Only one stage in the entire system can be marked as the completed (Done) stage."))

    @api.constrains('cancelled')
    def _check_cancelled_stage(self):
        """ Ensure that only one stage can be marked as 'Cancelled' in the system. """
        for stage in self:
            if stage.cancelled:
                other_cancelled_stages = self.search([('cancelled', '=', True), ('id', '!=', stage.id)])
                if other_cancelled_stages:
                    raise ValidationError(_("Only one stage in the system can be marked as the cancelled stage."))

    @api.constrains('in_progress', 'done', 'cancelled')
    def _check_stage_type_exclusive(self):
        """ Ensure a stage is exclusively marked as either 'In Progress', 'Done', or 'Cancelled'. """
        for stage in self:
            if sum([stage.in_progress, stage.done, stage.cancelled]) > 1:
                raise ValidationError(_("A stage can only be marked as one of 'In Progress', 'Done', or 'Cancelled'."))

