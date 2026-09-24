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
from odoo import models


class ProjectProject(models.Model):
    """When is_fsm is enabled on a project, auto-create field.service.request
    records for all existing tasks of that project."""

    _inherit = 'project.project'

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_fsm'):
            for project in self.filtered('is_fsm'):
                tasks = self.env['project.task'].search([
                    ('project_id', '=', project.id),
                ])
                tasks._create_fsm_request()
        return res