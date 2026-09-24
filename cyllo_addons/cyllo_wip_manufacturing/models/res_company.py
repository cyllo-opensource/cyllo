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


class ResCompany(models.Model):
    _inherit = 'res.company'

    wip_active = fields.Boolean(string="Enable WIP", default=False)
    wip_journal_id = fields.Many2one('account.journal', string="WIP Journal", check_company=True)
    wip_account_id = fields.Many2one('account.account', string="WIP Account", check_company=True)
    wip_overhead_account_id = fields.Many2one('account.account', string="WIP Overhead Account", check_company=True)

    def _register_hook(self):
        res = super()._register_hook()
        from odoo import api, SUPERUSER_ID
        from ..hooks import _set_wip_defaults

        _set_wip_defaults(api.Environment(self.env.cr, SUPERUSER_ID, {}))
        return res
