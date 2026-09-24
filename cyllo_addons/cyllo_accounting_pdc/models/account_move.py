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
from odoo import _, api, fields, models


class AccountMove(models.Model):
    """Inheriting account.move for adding new button for pdc payment"""
    _inherit = 'account.move'

    pdc_payment_id = fields.Many2one(comodel_name='account.pdc.payment',
                                     string="Payment", index='btree_not_null',
                                     copy=False, check_company=True)
    pdc_reference = fields.Char("Cheque Status")
    pdc_payment_ids = fields.One2many('account.pdc.payment', 'move_id',
                                      string='PDC Payments')

    @api.depends('move_type')
    def _compute_journal_id(self):
        """compute journal for pdc payment"""
        res = super()._compute_journal_id()
        if self._context.get('pdc_payment'):
            for record in self:
                company = record.company_id or self.env.company
                journal = self.env['account.journal'].search(
                    [*self.env['account.journal']._check_company_domain(
                        company), ('type', '=', 'bank')], limit=1)
                record.journal_id = journal.id
        return res

    def action_register_pdc_payment(self):
        """ Register PDC Payments: Open the PDC Payment Wizard"""
        return {
            'name': _('Register PDC Payment'),
            'res_model': 'account.pdc.payment.register',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'context': {'active_model': 'account.move', 'active_ids': self.ids},
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
