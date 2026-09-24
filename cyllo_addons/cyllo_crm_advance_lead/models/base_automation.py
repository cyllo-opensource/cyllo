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

from odoo import models, fields, api


class BaseAutomation(models.Model):
    _inherit = 'base.automation'

    temporary_filter_pre_domain = fields.Char(
        string='Temporary Before Update Domain',
        readonly=True,
        help="If present, this condition must be satisfied before the update of the record.")


    @api.onchange('trigger')
    def _onchange_trigger(self):
        """
        Prevent filter_pre_domain from being cleared when trigger changes.
        Only update it if temporary_filter_pre_domain has a value.
        """
        if self.temporary_filter_pre_domain:
            self.filter_pre_domain = self.temporary_filter_pre_domain

    @api.model
    def create(self, vals):
        """
        Ensure filter_pre_domain is preserved on record creation.
        """
        result = super(BaseAutomation, self).create(vals)

        result.write({
            'filter_pre_domain': result.temporary_filter_pre_domain
        })
        return result
