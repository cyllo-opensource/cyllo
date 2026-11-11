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

from odoo import api, fields, models
class ResUsers(models.Model):
    _inherit = "res.users"

    issue_raised_count=fields.Integer(string="Issue raised count",compute="_compute_issue_raised_count")

    def _compute_issue_raised_count(self):
        """ Function for  Computing  issue raised count by perticular user  """
        issue_report_ids=self.env['issue.report'].search([('user_id','=',self.id)])
        self.issue_raised_count=len(issue_report_ids)

    def action_open_raised_issues(self):
        """ Function for  Opening Issues raised by perticular user  """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Raised Issues',
            'res_model': 'issue.report',
            'domain': [('user_id', '=', self.id)],
            'view_mode': 'list,form',
            'target': 'self',
        }