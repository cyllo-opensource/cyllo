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

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class IntercompanyCommon(AccountTestInvoicingCommon):
    """Shared fixtures: two companies (A = company_1, B = company_2)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.company_data['company']
        cls.company_b = cls.company_data_2['company']
        cls.env.user.company_ids |= cls.company_a | cls.company_b
        cls.env = cls.env(context=dict(
            cls.env.context,
            allowed_company_ids=(cls.company_a | cls.company_b).ids,
        ))
        cls.env.user.company_id = cls.company_a
        if 'account.fiscal.year' in cls.env:
            # Cyllo accounting refuses to post outside an open fiscal year.
            year = fields.Date.today().year
            for company in (cls.company_a, cls.company_b):
                cls.env['account.fiscal.year'].with_company(company).create({
                    'name': 'FY %s %s' % (year, company.id),
                    'start_date': '%s-01-01' % year,
                    'end_date': '%s-12-31' % year,
                    'company_id': company.id,
                    'state': 'open',
                })
        cls.partner_a = cls.company_a.partner_id
        cls.partner_b = cls.company_b.partner_id
        cls.external_partner = cls.env['res.partner'].create({
            'name': 'External Partner',
        })
        cls.storable = cls.env['product.product'].create({
            'name': 'Intercompany Storable',
            'detailed_type': 'product',
            'list_price': 100.0,
            'standard_price': 60.0,
            'company_id': False,
        })

    @classmethod
    def _set_params(cls, **params):
        icp = cls.env['ir.config_parameter'].sudo()
        for key, value in params.items():
            icp.set_param('cyllo_intercompany_transfer.%s' % key, value)

    def _create_so(self, partner, qty=5.0, price=200.0, company=None):
        company = company or self.company_a
        return self.env['sale.order'].with_company(company).create({
            'partner_id': partner.id,
            'company_id': company.id,
            'order_line': [(0, 0, {
                'product_id': self.storable.id,
                'product_uom_qty': qty,
                'price_unit': price,
            })],
        })

    def _create_po(self, partner, qty=10.0, price=100.0, company=None):
        company = company or self.company_a
        return self.env['purchase.order'].with_company(company).create({
            'partner_id': partner.id,
            'company_id': company.id,
            'order_line': [(0, 0, {
                'product_id': self.storable.id,
                'product_qty': qty,
                'price_unit': price,
            })],
        })
