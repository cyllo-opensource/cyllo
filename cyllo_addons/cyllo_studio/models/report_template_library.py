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


class CylloReportTemplate(models.Model):
    _name = 'cyllo.report.template'
    _description = 'Cyllo Report Template'
    _order = 'write_date desc, name'

    name = fields.Char(required=True, index=True)
    description = fields.Text()
    category = fields.Char(index=True)
    source_report_id = fields.Many2one(
        'ir.actions.report',
        string='Source Report',
        ondelete='set null',
    )
    source_model = fields.Char(string='Source Model')
    source_template = fields.Char(string='Source Template')
    doc_template = fields.Char(string='Document Template')
    payload_json = fields.Text(string='Template Payload')
    active = fields.Boolean(default=True)
