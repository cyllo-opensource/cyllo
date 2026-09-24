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
from odoo import api, fields, models


class DocumentRequestTemplate(models.Model):
    """Model representing document request templates."""
    _name = "document.request.template"
    _description = "document request template"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Template name", required=True, help="name of template")
    user_ids = fields.Many2many('res.users', help="Choose User", compute='_compute_user_ids')
    company_id = fields.Many2one('res.company', help='choose company',
                                 default=lambda self: self.env.company)
    manager_id = fields.Many2one("res.users", string="Managers", help="Choose Manager", required=True)
    stamp = fields.Image(max_width=170, max_height=170, help="Add your stamp")
    template = fields.Html(help="Add the template here")

    @api.depends('name')
    def _compute_user_ids(self):
        """function to get user's with document request template manager group"""
        self.user_ids = self.manager_id.search([]).filtered(
            lambda managers: managers.has_group('cyllo_documents.group_cyllo_documents_manager'))
