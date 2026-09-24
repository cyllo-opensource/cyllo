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
from datetime import datetime, timedelta

from odoo import _, fields
from odoo.exceptions import UserError
from odoo.tools import end_of
from odoo.addons.cyllo_asset_management.tests.common import TestCommon


class TestAssetAsset(TestCommon):

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()
        asset = cls.asset
        asset.modified_asset_ids = asset.ids
        asset.asset_item_id.purchase_date = '3000-1-12'
        asset.status = 'sell'
        cls.asset.update({'depreciation_line_ids': [(fields.Command.link(cls.depreciation_line.id))]})
        cls.depreciation_line_2 = cls.env['asset.depreciation.line'].create({'depreciation_id': cls.asset.id,
                                                                             'year': 1593,
                                                                             'date': fields.date.today(),
                                                                             'company_id': cls.company.id})
        cls.account_move_2 = cls.env['account.move'].create({
            'name': 'TestInv02',
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'date': end_of(fields.date.today(), granularity='month'),
            'invoice_date': fields.date.today(),
            'amount_total_signed': 1111,
            'depreciation_line_id': cls.depreciation_line_2.id,
            'line_ids': [(fields.Command.create({
                'name': 'Test move line',
                'product_id': cls.env.ref("product.product_product_4").id,
                'quantity': 2,
                'balance': 4,
                'account_id': cls.account_2.id,
            }))]
        })
        cls.account_move_3 = cls.env['account.move'].create({
            'name': 'TestInv03',
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'date': end_of(fields.date.today(), granularity='month'),
            'invoice_date': fields.date.today(),
            'depreciation_line_id': cls.depreciation_line_2.id,
            'line_ids': [(fields.Command.create({
                'name': 'Test move line',
                'product_id': cls.env.ref("product.product_product_4").id,
                'quantity': 2,
                'balance': 4,
                'account_id': cls.account_2.id,
            }))]
        })
        modified_asset_id = cls.env['asset.asset'].create({
            'name': 'XYZ',
            'asset_item_id': cls.item_id.id,
            'asset_type_id': cls.asset_type.id,
            'original_value': 5,
            'salvage_value': 5,
            'status': 'draft',
            'depreciation_method': 'straight_line',
            'computation_method': 'no_prorata',
        })
        cls.asset_asset = cls.env['asset.asset'].create({
            'name': 'XYZ',
            'asset_item_id': cls.item_id.id,
            'asset_type_id': cls.asset_type.id,
            'original_value': 4,
            'salvage_value': 4,
            'is_depreciate': True,
            'status': 'draft',
            'depreciation_method': 'straight_line',
            'computation_method': 'no_prorata',
            'modified_asset_ids': modified_asset_id.ids
        })

    def test_check_original_value(self):
        self.asset._check_original_value()
        self.assertEqual(self.asset.original_value, abs(self.asset.original_value))
        self.asset.original_value = 2
        with self.assertRaises(UserError):
            self.asset.original_value = -1

    def test_compute_modified_count(self):
        self.asset._compute_modified_count()
        self.assertEqual(self.asset.modified_count, len(self.asset.modified_asset_ids))

    def test_onchange_depreciating_factor(self):
        self.asset.depreciating_factor = -5
        self.asset._onchange_depreciating_factor()
        self.assertEqual(self.asset.depreciating_factor, abs(-5))

    def test_onchange_depreciation_date(self):
        self.asset.depreciation_date = '3000-1-1'
        with self.assertRaises(UserError):
            self.asset._onchange_depreciation_date()

    def test_onchange_prorata_date(self):
        self.asset.prorata_date = '3000-1-1'
        with self.assertRaises(UserError):
            self.asset._onchange_prorata_date()

    def test_onchange_salvage_value(self):
        self.asset.salvage_value = -5
        self.asset._onchange_salvage_value()
        self.assertEqual(self.asset.salvage_value, abs(-5))
        self.asset.salvage_value = 4
        with self.assertRaises(UserError):
            self.asset._onchange_salvage_value()

    def test_onchange_day_amount(self):
        self.asset.day_amount = -5
        with self.assertRaises(UserError):
            self.asset._onchange_day_amount()

    def test_action_request_assets(self):
        with self.assertRaises(UserError):
            self.asset.action_request_assets()

    def test_action_reserve_assets(self):
        with self.assertRaises(UserError):
            self.asset.action_reserve_assets()
        self.asset.status = 'draft'
        self.asset.is_reserve = True
        with self.assertRaises(UserError):
            self.asset.action_reserve_assets()
        self.asset.is_reserve = False
        self.assertEqual(self.asset.action_reserve_assets(),
                         {'name': _('Reservation'),
                          'view_mode': 'form',
                          'view_id': self.env.ref('cyllo_asset_management.view_asset_reservation_form2').id,
                          'res_model': 'asset.reservation',
                          'type': 'ir.actions.act_window',
                          'context': {'default_asset_id': self.asset.id, },
                          'target': 'new'})

    def test_action_assign_assets(self):
        self.asset.status = 'draft'
        self.assertEqual(self.asset.action_assign_assets(),
                         {'name': 'Assign', 'view_mode': 'form', 'view_id': self.env.ref('cyllo_asset_management.view_asset_assign_form2').id, 'res_model': 'asset.assign',
                          'type': 'ir.actions.act_window',
                          'context': {'default_asset_id': self.asset.id,
                                      'default_employee_id': self.reserved_asset.employee_id.id}, 'target': 'new'})
        self.asset.is_assign = True
        with self.assertRaises(UserError):
            self.asset.action_assign_assets()

    def test_action_lease_assets(self):
        asset = self.asset
        self.asset.is_lease_asset = False
        with self.assertRaises(UserError):
            asset.action_lease_assets()
        asset.is_lease_asset, asset.status, self.reserved_asset.status = True, 'draft', 'draft'
        self.assertEqual(asset.action_lease_assets(),
                         {'name': 'Lease', 'view_mode': 'form',
                          'view_id': self.env.ref('cyllo_asset_management.view_asset_lease_form2').id,
                          'res_model': 'asset.lease',
                          'type': 'ir.actions.act_window',
                          'context': {'default_asset_id': asset.id, 'default_customer_id': ''}, 'target': 'new'})
        asset.is_reserve = True

    def test_action_rent_assets(self):
        asset = self.asset
        asset.is_rental_asset = False
        with self.assertRaises(UserError):
            asset.action_rent_assets()
        self.reserved_asset.status = 'draft'
        asset.is_assign, asset.status, asset.is_rental_asset = False, 'draft', True
        self.assertEqual(asset.action_rent_assets(),
                         {'name': 'Rental', 'view_mode': 'form',
                          'view_id': self.env.ref('cyllo_asset_management.view_asset_rental_form2').id,
                          'res_model': 'asset.rental',
                          'type': 'ir.actions.act_window',
                          'context': {'default_asset_id': asset.id, 'default_customer_id': ''}, 'target': 'new'})

    def test_action_repair_assets(self):
        asset = self.asset
        self.asset.status = 'sell'
        self.reserved_asset.status = 'reserve'
        with self.assertRaises(UserError):
            asset.action_repair_assets()
        asset.is_lease, asset.status, asset.is_reserve = True, 'draft', True
        leased_asset = self.env['asset.lease'].create({
            'asset_id': asset.id,
            'start_date': '2000-1-1',
            'end_date': '2005-1-1',
            'status': 'lease',
            'lease_amount': 8555,
            'customer_id': self.partner.id
        })
        self.employee.work_contact_id = leased_asset.customer_id.id
        expected_action = {
            'name': 'Repair',
            'view_mode': 'form',
            'res_model': 'asset.repair',
            'type': 'ir.actions.act_window',
            'context': {'default_asset_id': asset.id, 'default_employee_id': self.employee.id},
            'target': 'new'
        }
        self.assertEqual(asset.action_repair_assets(), expected_action)
        asset.is_assign, asset.is_lease = True, False
        expected_action['context']['default_employee_id'] = self.reserved_asset.employee_id.id
        self.assertEqual(asset.action_repair_assets(), expected_action)
        asset.is_assign, asset.is_rental = False, True
        self.employee.work_contact_id = self.env.user.partner_id.id
        expected_action['context']['default_employee_id'] = self.employee.id
        self.assertEqual(asset.action_repair_assets(), expected_action)

    def test_action_maintenance_assets(self):
        asset = self.asset
        self.reserved_asset.status = 'reserve'
        with self.assertRaises(UserError):
            asset.action_maintenance_assets()
        asset.is_lease, asset.status, asset.is_reserve = True, 'draft', True
        leased_asset = self.env['asset.lease'].create({
            'asset_id': asset.id,
            'start_date': '2000-1-1',
            'end_date': '2005-1-1',
            'status': 'lease',
            'lease_amount': 8555,
            'customer_id': self.partner.id
        })
        self.employee.work_contact_id = leased_asset.customer_id.id
        expected_action = {
            'name': 'Maintenance',
            'view_mode': 'form',
            'res_model': 'asset.maintenance',
            'type': 'ir.actions.act_window',
            'context': {'default_asset_id': asset.id, 'default_employee_id': self.employee.id},
            'target': 'new'
        }
        self.assertEqual(asset.action_maintenance_assets(), expected_action)
        asset.is_assign, asset.is_lease = True, False
        expected_action['context']['default_employee_id'] = self.reserved_asset.employee_id.id
        self.assertEqual(asset.action_maintenance_assets(), expected_action)
        asset.is_assign, asset.is_rental = False, True
        self.employee.work_contact_id = self.env.user.partner_id.id
        expected_action['context']['default_employee_id'] = self.employee.id
        self.assertEqual(asset.action_maintenance_assets(), expected_action)

    def test_action_lost_missing_assets(self):
        asset = self.asset
        self.asset.status = 'draft'
        self.account_move.state = 'posted'
        self.account_move.date = datetime.today() + timedelta(days=1)
        window_action = {
            'name': _('Lost'),
            'view_mode': 'form',
            'res_model': 'asset.lost',
            'type': 'ir.actions.act_window',
            'context': {
                'default_asset_asset_id': self.asset.id,
                'default_is_posted': False
            }, 'target': 'new'}
        with self.assertRaises(UserError):
            asset.action_lost_missing_assets()
        asset.is_entry = True
        self.account_move.state = 'draft'
        self.assertEqual(asset.action_lost_missing_assets(), window_action)
        self.account_move.state = 'cancel'
        window_action['context']['default_is_posted'] = True
        asset.action_lost_missing_assets()
        self.assertEqual(asset.action_lost_missing_assets(), window_action)
        asset.is_entry = False
        asset.action_lost_missing_assets()
        self.assertEqual(asset.status, 'lost')

    def test_action_sell_dispose_assets(self):
        asset = self.asset
        self.asset.status = 'draft'
        window_action = {'name': _('Sell/Dispose'),
                         'view_mode': 'form',
                         'res_model': 'asset.sell.dispose',
                         'type': 'ir.actions.act_window',
                         'context': {
                             'default_asset_asset_id': self.asset.id,
                             'default_is_posted': True
                         }, 'target': 'new'}
        self.account_move.state = 'cancel'
        self.assertEqual(asset.action_sell_dispose_assets(), window_action)

    def test_action_view_reservation(self):
        """Test whether function returns reservation window action """
        self.assertEqual(self.asset.action_view_reservation(), {
            'name': 'Reservation',
            'view_mode': 'form',
            'res_id': self.reserved_asset.id,
            'res_model': 'asset.reservation',
            'type': 'ir.actions.act_window',
        })

    def test_action_view_lease(self):
        """Test action view lease"""
        leased_asset = self.env['asset.lease'].search([('asset_id', '=', self.asset.id), ('status', '=', 'lease')])
        self.assertEqual(self.asset.action_view_lease(), {
            'name': 'Lease',
            'view_mode': 'form',
            'res_model': 'asset.lease',
            'res_id': leased_asset.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        })

    def test_viewing_actions(self):
        """Test repair, maintenance, rental, journal entries and assign viewing action"""
        rental_asset = self.env['asset.rental'].search([('asset_id', '=', self.asset.id), ('status', '=', 'rent')])
        self.assertEqual(self.asset.action_view_rental(), {
            'name': 'Rental',
            'view_mode': 'form',
            'res_id': rental_asset.id,
            'res_model': 'asset.rental',
            'type': 'ir.actions.act_window',
        })
        self.assertEqual(self.asset.action_view_repair(), {
            'name': 'Repair Assets',
            'view_mode': 'form',
            'res_id': self.asset_repair.id,
            'res_model': 'account.asset.repair',
            'type': 'ir.actions.act_window',
        })
        self.assertEqual(self.asset.action_view_maintenance(), {
            'name': 'Maintenance assets',
            'view_mode': 'form',
            'res_id': self.asset_maintenance.id,
            'res_model': 'account.asset.maintenance',
            'type': 'ir.actions.act_window',
        })
        self.assertEqual(self.asset.action_view_maintenance(), {
            'name': 'Maintenance assets',
            'view_mode': 'form',
            'res_id': self.asset_maintenance.id,
            'res_model': 'account.asset.maintenance',
            'type': 'ir.actions.act_window',
        })
        assigned_asset = self.env['asset.assign'].create({
            'asset_id': self.asset.id,
            'company_id': self.company.id,
            'employee_id': self.employee.id,
            'status': 'assign',
            'assign_date': '6511-5-7',
        })
        self.assertEqual(self.asset.action_view_assign(), {
            'name': 'Assign',
            'view_mode': 'form',
            'res_id': assigned_asset.id,
            'res_model': 'asset.assign',
            'type': 'ir.actions.act_window',
            'domain': [('asset_id', '=', self.asset.id), ('status', '=', 'assign')]
        })
        self.assertEqual(self.asset.action_view_journal_entries(), {
            'name': 'Journal Entries',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('asset_asset_id', '=', self.asset.id)]
        })

    def test_compute_entry_count(self):
        """Tests _compute_entry_count"""
        self.asset._compute_entry_count()
        self.assertEqual(len(self.asset.depreciated_entry_ids), self.asset.entry_count)

    def test_create_journal_entries(self):
        """Tests journal entries creating function"""
        self.asset.asset_depreciation_account_id = self.account_1.id
        self.asset.currency_id = self.currency_id.id
        self.asset.asset_journal_id = self.asset_journal_id.id
        self.depreciation_line.date = fields.Date.today()
        self.depreciation_line.depreciation_expense = 5622
        self.asset.update({'depreciation_line_ids': [(fields.Command.link(self.depreciation_line.id))]})
        self.asset._create_journal_entries()
        self.assertEqual(self.env['account.move'].search([], order='id desc', limit=1).state, 'posted')

    def test_action_confirm_deprecation(self):
        """"""
        self.asset.original_value = 0
        with self.assertRaises(UserError):
            self.asset.action_confirm_deprecation()
        self.asset.original_value = 4
        self.asset.action_confirm_deprecation()
        self.assertEqual(self.asset.status, 'running')
        self.assertEqual(self.asset.is_confirm, True)

    def test_action_compute_depreciation(self):
        """Tests compute depreciation action"""
        self.asset.original_value = 0
        result = self.asset.action_compute_depreciation()
        self.assertEqual(self.asset.depreciation_line_ids.ids, [])
        self.assertEqual(self.asset.is_depreciate, False)
        self.assertEqual(self.asset.salvage_value, self.asset.original_value)
        self.assertEqual(result, self.asset)
        self.asset.original_value = 4
        self.asset.action_compute_depreciation()
        self.assertEqual(self.asset.original_value, self.asset.salvage_value)

    def test_action_cancel_asset(self):
        """Tests of button action for the cancelling the asset"""
        self.asset.is_reserve = True
        self.assertEqual(self.asset.action_cancel_asset(), {
            'name': 'Assets Cancel warning',
            'view_mode': 'form',
            'res_model': 'asset.cancel.warning',
            'type': 'ir.actions.act_window',
            'context': {
                'default_asset_id': self.asset.id,
            },
            'target': 'new'
        })
        self.asset.is_reserve = False
        self.asset.action_cancel_asset()
        self.assertEqual(self.asset.depreciated_entry_ids.ids, [])
        self.assertEqual(self.asset.status, 'cancel')
        self.asset.action_cancel_asset()
        self.assertEqual(self.asset.status, 'cancel')

    def test_action_modify_asset(self):
        """Tests button action for the modifying the asset"""
        self.asset.is_revaluate = True
        self.asset.depreciated_entry_ids.fiscal_year_id.state = 'open'
        self.asset.depreciated_entry_ids.state = 'posted'
        self.asset.depreciated_entry_ids.date = fields.date.today() + timedelta(days=5)
        with self.assertRaises(UserError):
            self.asset.action_modify_asset()
        self.asset.depreciated_entry_ids.state = 'draft'
        self.asset.action_modify_asset()
        self.assertEqual(self.asset.is_revaluate, False)
        self.assertEqual(self.asset.action_modify_asset(), {
            'name': _('Modify Asset'),
            'view_mode': 'form',
            'res_model': 'asset.modify',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_asset_asset_id': self.asset.id,
                'default_asset_journal_id': self.asset.asset_journal_id.id,
                'default_fixed_asset_account_id': self.asset.fixed_asset_account_id.id,
                'default_asset_depreciation_account_id': self.asset.asset_depreciation_account_id.id,
                'default_asset_expense_account_id': self.asset.asset_expense_account_id.id,
                'default_salvage_value': self.asset.salvage_value,
                'default_depreciation_method': self.asset.depreciation_method,
                'default_duration_period': self.asset.duration_period,
                'default_method_duration': self.asset.method_duration,
                'default_depreciation_date': self.asset.depreciation_date,
            }
        })

    def test_action_revaluate_asset(self):
        """Tests the button action for the revaluating the asset,
        this incliudes tests of create_modify_asset, """
        self.asset.duration_period = 'month'
        self.asset.computation_method = 'no_prorata'
        self.asset.update({'depreciated_entry_ids': [(fields.Command.link(self.account_move.id))]})
        self.asset.update({'depreciated_entry_ids': [(fields.Command.link(self.account_move_2.id))]})
        for move in self.asset.depreciated_entry_ids:
            move._post()
            break
        self.asset.action_revaluate_asset()
        for i in self.asset.depreciated_entry_ids:
            i.date = end_of(fields.date.today(), granularity='year')
            break
        self.assertEqual(self.asset.is_modify, False)
        self.assertEqual(self.asset.is_confirm, True)
        self.asset.duration_period = 'year'
        self.depreciation_line.date = end_of(fields.date.today() + timedelta(days=100), granularity='year')
        self.asset.update({'depreciation_line_ids': [(fields.Command.link(self.depreciation_line.id))]})
        self.asset.update({'depreciated_entry_ids': [(fields.Command.link(self.account_move.id))]})
        self.asset.action_revaluate_asset()

    def test_action_reset_to_draft(self):
        """tests action_reset_to_draft function"""
        asset = self.asset_asset
        asset.update({'depreciation_line_ids': [(fields.Command.link(self.depreciation_line.id))]})
        asset.update({'depreciated_entry_ids': [(fields.Command.link(self.account_move.id)),
                                               (fields.Command.link(self.account_move_3.id))]})
        depr_entry_ids = asset.depreciated_entry_ids
        self.account_move.fiscal_year_id.state = 'open'
        depr_entry_ids[0].state, depr_entry_ids[1].state, first_depr_entry_id = 'posted', 'draft', depr_entry_ids[0]
        asset.action_reset_to_draft()
        self.assertEqual(asset.depreciated_entry_ids.ids, [])
        self.assertEqual(len(asset.depreciated_entry_ids), 0)
        self.assertEqual(len(asset.modified_asset_ids), 0)
        self.assertEqual(len(asset.depreciation_line_ids), 0)
        self.assertEqual(asset.status, 'draft')
        self.assertEqual(asset.is_depreciate, False)
        self.assertEqual(asset.is_entry, False)
        self.assertEqual(asset.is_modify, False)
        self.assertEqual(asset.is_confirm, False)
        self.assertEqual(asset.is_reserve, False)
        self.assertEqual(asset.is_assign, False)
        self.assertEqual(asset.is_lease, False)
        self.assertEqual(asset.is_rental, False)
        self.assertEqual(asset.is_repair, False)
        self.assertEqual(asset.is_maintenance, False)
        self.assertEqual(asset.is_sell, False)
        self.assertEqual(asset.is_dispose, False)
        self.assertEqual(asset.is_lost, False)
        self.assertEqual(asset.modify_value, 0)
        self.assertEqual(asset.is_revaluate, False)
        self.assertEqual(asset.is_decrease_value, False)
        
    def test_action_view_modified_asset(self):
        """Test for function for the viewing the modified asset"""
        self.assertEqual(self.asset.action_view_modified_asset(), {
            'name': 'Asset',
            'view_mode': 'tree,form',
            'res_model': 'asset.asset',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.asset.modified_asset_ids.ids)]
        })
    def test_unlink(self):
        """Test for asset unlink function"""
        asset = self.asset_asset
        asset.status = 'running'
        with self.assertRaises(UserError):
            asset.unlink()
        asset.is_assign = True
        with self.assertRaises(UserError):
            asset.unlink()
        asset.is_assign = False
        asset.status = 'sell'
        self.assertEqual(asset.unlink(), True)