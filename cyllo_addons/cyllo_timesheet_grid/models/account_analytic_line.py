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
from odoo import api, models


class AccountAnalyticLine(models.Model):
    """
        Extends the base 'account.analytic.line' model to include a custom
        method 'write_task'.
    """
    _inherit = "account.analytic.line"

    @api.model
    def write_task(self, vals):
        """
            Update the 'task_id' field of the associated 'analytic_account_id'
            record with the provided value.
            :param vals: A dictionary containing values to update.
            :return: True if the operation is successful.
        """
        analytic_account_id = self.browse(vals.get('analytic_account_id'))
        analytic_account_id.update({
            'task_id': vals.get('task_id')
        })
        return True
