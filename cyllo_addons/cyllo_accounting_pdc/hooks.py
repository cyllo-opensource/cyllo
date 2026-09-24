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
def _add_payment_methods(env):
    """To get the pdc inbound and outbound methods after the module installation"""
    journals = env['account.journal'].search([('type', '=', 'bank')])
    for journal in journals:
        journal._compute_outbound_payment_method_line_ids()
        journal._compute_inbound_payment_method_line_ids()
        journal._compute_available_payment_method_ids()


def _set_pdc_account(env):
    """Create PDC account(type=current_asset) for PDC payment"""
    company = env.company
    pdc_account_code = 111220
    while env['account.account'].search([
        *env['account.account']._check_company_domain(company or False),
        ('code', '=', str(pdc_account_code)),
    ]):
        pdc_account_code -= 1
    env['account.account'].create({
        'code': str(pdc_account_code),
        'name': 'PDC Payment',
        'account_type': 'asset_current',
        'company_id': company.id,
        'reconcile': True,
    })


def _post_init_account(env):
    """Functions will execute after the module installation"""
    _add_payment_methods(env)
    _set_pdc_account(env)
