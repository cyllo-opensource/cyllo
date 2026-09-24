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

def _set_wip_defaults(env):
    companies = env['res.company'].search([('chart_template', '!=', False)])
    for company in companies:
        journal = env.ref(f'account.{company.id}_inventory_valuation', raise_if_not_found=False)
        overhead_account = env.ref(f'account.{company.id}_cost_of_production', raise_if_not_found=False)

        wip_account = env.ref(f'cyllo_wip_manufacturing.{company.id}_wip_current_assets', raise_if_not_found=False)
        if not wip_account:
            wip_account = env['account.account'].create({
                'name': 'Work In Progress',
                'code': '110500',
                'account_type': 'asset_current',
                'reconcile': True,
                'company_id': company.id,
            })
            env['ir.model.data']._update_xmlids([{
                'xml_id': f'cyllo_wip_manufacturing.{company.id}_wip_current_assets',
                'record': wip_account,
                'noupdate': True,
            }])

        values = {}
        if journal and not company.wip_journal_id:
            values['wip_journal_id'] = journal.id
        if wip_account and not company.wip_account_id:
            values['wip_account_id'] = wip_account.id
        if overhead_account and not company.wip_overhead_account_id:
            values['wip_overhead_account_id'] = overhead_account.id

        if values:
            company.write(values)

def post_init_hook(env):
    _set_wip_defaults(env)
