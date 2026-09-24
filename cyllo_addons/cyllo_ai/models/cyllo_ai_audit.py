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
"""Immutable audit trail for data-modifying actions performed by Cyllo AI.

Every confirmed create/update/delete executed through the AI's typed CRUD path
writes one entry here (via sudo, so logging never depends on the acting user's
rights on this model). Entries are read-only for administrators and are never
edited or deleted by the engine.
"""
from odoo import fields, models


class CylloAiAudit(models.Model):
    _name = 'cyllo.ai.audit'
    _description = 'Cyllo AI Action Audit Log'
    _order = 'create_date desc'
    _rec_name = 'model_name'

    user_id = fields.Many2one(
        'res.users', string='User', required=True, readonly=True,
        help='The user on whose behalf the action was executed.')
    model_name = fields.Char(
        string='Model', readonly=True, index=True,
        help='Technical name of the model that was acted on.')
    action = fields.Selection(
        [('create', 'Create'), ('update', 'Update'), ('delete', 'Delete')],
        string='Action', readonly=True, index=True)
    record_ids = fields.Char(
        string='Record IDs', readonly=True,
        help='JSON list of the affected record ids.')
    values = fields.Text(
        string='Values', readonly=True,
        help='JSON of the values written (empty for deletes).')
