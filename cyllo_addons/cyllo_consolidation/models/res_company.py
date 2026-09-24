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


class ResCompany(models.Model):
    """This model inherits from the 'res.company' model to provide additional
     features and modifications specific to the application's requirements."""
    _inherit = 'res.company'

    def action_open_mapped_accounts(self):
        """This action opens a window displaying the mapped accounts for this
        company."""
        return {
            'type': 'ir.actions.act_window',
            'name': f"Account Mapping: {self.name}",
            'view_mode': 'tree,form',
            'res_model': 'account.account',
            'target': 'current',
            'domain': [('company_id', '=', self.id)],
        }
