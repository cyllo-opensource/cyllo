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


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    wip_active = fields.Boolean(
        related='company_id.wip_active',
        readonly=False,
        string="Enable WIP"
    )
    wip_journal_id = fields.Many2one(
        'account.journal',
        related='company_id.wip_journal_id',
        readonly=False,
        string="WIP Journal"
    )
    wip_account_id = fields.Many2one(
        'account.account',
        related='company_id.wip_account_id',
        readonly=False,
        string="WIP Account"
    )
    wip_overhead_account_id = fields.Many2one(
        'account.account',
        related='company_id.wip_overhead_account_id',
        readonly=False,
        string="WIP Overhead Account"
    )
