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
import math
import calendar
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Date
from odoo.tools.date_utils import end_of


class AssetAsset(models.Model):
    _name = 'asset.asset'
    _description = 'Asset Assets'
    _inherit = ['mail.thread']

    name = fields.Char(
        string="Asset",
        required=True,
        translate=True
    )
    asset_item_id = fields.Many2one(
        "asset.item"
    )
    brand_id = fields.Many2one(
        string="Brand",
        comodel_name='asset.brand'
    )
    serial_no = fields.Char(
        string="Serial No."
    )
    vendor_id = fields.Many2one(
        "res.partner",
        string="Purchase From",
        copy=False
    )
    date = fields.Date(
        string="Purchase Date",
        default=fields.Date.context_today,
        required=True
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company, help='Select the company'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        help='Currency of company'
    )
    status = fields.Selection(
        [('draft', 'Draft'), ('running', 'Running'), ('reserved', 'Reserved'), ('leased', 'Leased'),
         ('assigned', 'Assigned'), ('rented', 'Rented'), ('sell', 'Sell'), ('disposed', 'Dispose'),
         ('cancel', 'Cancelled')],
        default="draft",
        copy=False,
        tracking=True,
    )
    is_confirm = fields.Boolean(
        string="Confirmed",
        copy=False
    )
    is_modify = fields.Boolean(
        string="Confirmed",
        copy=False
    )
    is_reserve = fields.Boolean(
        string="Reserved",
        copy=False
    )
    is_assign = fields.Boolean(
        string="Assigned",
        copy=False
    )
    is_lease = fields.Boolean(
        string="Leased",
        copy=False
    )
    is_rental = fields.Boolean(
        string="Rental",
        copy=False
    )
    is_repair = fields.Boolean(
        string="Repair",
        copy=False
    )
    is_maintenance = fields.Boolean(
        string="Maintenance",
        copy=False
    )
    is_sell = fields.Boolean(
        string="Sell",
        copy=False
    )
    is_dispose = fields.Boolean(
        string="Dispose",
        copy=False
    )
    is_lost = fields.Boolean(
        string="Loss",
        copy=False
    )
    is_depreciate = fields.Boolean(
        string="Depreciate",
        copy=False
    )
    is_entry = fields.Boolean(
        string="Entry",
        copy=False
    )
    is_lease_asset = fields.Boolean()
    is_rental_asset = fields.Boolean()
    is_revaluate = fields.Boolean()
    is_decrease_value = fields.Boolean()
    day_amount = fields.Float()
    week_amount = fields.Float()
    month_amount = fields.Float()
    year_amount = fields.Float()
    parent_id = fields.Many2one('asset.asset')
    maintenance_state = fields.Selection(
        [('maintenance', 'Under Maintenance'), ('repair', 'Under Repair')],
        compute='_compute_maintenance_state', store=False)
    depreciation_method = fields.Selection(
        [('straight_line', 'Straight Line'), ('declining_balance', 'Declining Balance'),
         ('declining_straight_line', 'Declining and Straight Line')],
        string='Method', readonly=False, required=True, default='straight_line')
    depreciation_date = fields.Date(default=fields.Date.context_today, tracking=True,
                                    string='Depreciation date')
    method_duration = fields.Integer(string="Duration", tracking=True, default=1, readonly=False)
    is_auto_calculate = fields.Boolean(string='Auto Calculate')
    depreciating_factor = fields.Float(default=0.3)
    duration_period = fields.Selection([('month', 'Month'), ('year', 'Year')], tracking=True,
                                       default='year',
                                       required=True)
    original_value = fields.Float(required=True)
    salvage_value = fields.Float(required=True, string='Depreciatable Value')
    modify_value = fields.Float()
    depreciation_line_ids = fields.One2many('asset.depreciation.line', 'depreciation_id',
                                            string='Asset Depreciation Line')
    fixed_asset_account_id = fields.Many2one('account.account', required=True,
                                             domain="[('account_type', 'in', ('asset_current', 'asset_fixed'))]")
    asset_depreciation_account_id = fields.Many2one('account.account',
                                                    string='Depreciation Asset Account',
                                                    required=True,
                                                    domain="[('account_type', 'in', ('asset_current', 'asset_fixed'))]")
    asset_expense_account_id = fields.Many2one('account.account', required=True,
                                               domain="[('account_type', '=', 'expense')]")
    asset_loss_account_id = fields.Many2one('account.account', required=True)
    asset_journal_id = fields.Many2one('account.journal', required=True,
                                       domain="[('type', '=', 'general')]")
    depreciated_entry_ids = fields.One2many('account.move', 'asset_asset_id',
                                            string='Depreciation Lines')
    modified_asset_ids = fields.Many2many('asset.asset', "asset_sub_table", 'asset_1', 'asset_2')
    computation_method = fields.Selection(
        [('no_prorata', 'No Prorata'), ('constant_period', 'Constant Period'),
         ('daily_compute', 'Daily Computation')],
        'Computation', tracking=True, readonly=False, required=True, default='no_prorata')
    prorata_date = fields.Date(default=fields.Date.context_today)
    entry_count = fields.Integer(compute='_compute_entry_count')
    maintenance_count = fields.Integer(compute='_compute_maintenance_count')
    modified_count = fields.Integer(compute='_compute_modified_count')
    invoice_id = fields.Many2one('account.move')
    invoice_line_id = fields.Many2one('account.move.line')
    active = fields.Boolean(default=True)
    depreciation_duration = fields.Integer()
    total_depreciation_days = fields.Integer()
    pre_salvage_value = fields.Float()
    reference_note = fields.Char()
    under_warranty = fields.Boolean(string="Warranty Included")
    warranty_period_type = fields.Selection(string="Period",
                                            selection=[('days', 'Days'), ('months', 'Months'),
                                                       ('years', 'Year')], default="days")
    warranty_period = fields.Integer()
    warranty_end_date = fields.Date(string="Warranty Upto", compute="_compute_warranty_end_date")
    under_insurance = fields.Boolean(string="Has Insurance")
    insurance_name_id = fields.Many2one(comodel_name='asset.asset.insurance', string="Type")
    insurance_number = fields.Char(string="ID")
    insurance_start_date = fields.Date(string="Start date")
    insurance_end_date = fields.Date(string="End date")
    reimburse_after_invoice = fields.Boolean(string="Reimburse After Invoice",
                                             help="Enable if insurance reimbursement happens after invoice creation.")
    warranty_attachment_ids = fields.Many2many('ir.attachment', 'asset_warranty_attachment_rel',
                                               'asset_id', 'attachment_id',
                                               string="Warranty Documents",
                                               domain="[('res_model', '=', 'asset.asset')]")
    insurance_attachment_ids = fields.Many2many('ir.attachment', 'asset_insurance_attachment_rel',
                                                'asset_id', 'attachment_id',
                                                string="Insurance Documents",
                                                domain="[('res_model', '=', 'asset.asset')]")
    buffer_duration = fields.Integer(string="Cool Down Duration", default=0,
                                     help="Number of days the asset remains unavailable after a booking ends")
    buffer_period = fields.Selection([('hour', 'Hour'), ('day', 'Day'), ('week', 'Week')],
                                     tracking=True,
                                     default='hour', required=True)
    automatic_maintenance = fields.Selection(
        [
            ('no', 'No Maintenance Required'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', '3 Months'),
            ('semi_annually', '6 Months'),
            ('yearly', 'Yearly'),
        ],
        string="Automatic Maintenance",
        default='no',
        help="Select frequency for automatic maintenance request generation."
    )
    last_maintenance_date = fields.Date(string="Last Maintenance Date")
    next_maintenance_date = fields.Date(string="Next Maintenance Date",
                                        compute="compute_next_maintenance_date", store=True)
    asset_lease_count = fields.Integer(string="Asset Lease Count", compute="_compute_asset_lease_count")

    def _compute_maintenance_state(self):
        """Compute maintenance states of assets"""
        for rec in self:
            if rec.is_repair:
                rec.maintenance_state = 'repair'
            elif rec.is_maintenance:
                rec.maintenance_state = 'maintenance'
            else:
                rec.maintenance_state = False

    @api.depends('modified_asset_ids')
    def _compute_modified_count(self):
        """Compute linked modified assets"""
        for rec in self:
            rec.modified_count = len(rec.modified_asset_ids)

    @api.depends('warranty_period', 'warranty_period_type')
    def _compute_warranty_end_date(self):
        for record in self:
            if record.warranty_period and record.warranty_period_type:
                if record.warranty_period_type == 'days':
                    record.warranty_end_date = record.date + relativedelta(
                        days=record.warranty_period)
                if record.warranty_period_type == 'months':
                    record.warranty_end_date = record.date + relativedelta(
                        months=record.warranty_period)
                if record.warranty_period_type == 'years':
                    record.warranty_end_date = record.date + relativedelta(
                        years=record.warranty_period)
            else:
                record.warranty_end_date = fields.Date.today()

    @api.depends('depreciated_entry_ids')
    def _compute_entry_count(self):
        """Compute entries count"""
        self.entry_count = len(self.depreciated_entry_ids)

    @api.depends('name')
    def _compute_maintenance_count(self):
        """Check count of asset repair and maintenance and its current stage"""
        for rec in self:
            maintenance = self.env['maintenance.request'].search([('asset_id', '=', rec.id)])
            rec.maintenance_count = len(maintenance)
            for record in maintenance:
                if record.stage_done == False:
                    if record.maintenance_type == 'corrective':
                        rec.is_repair = True
                    elif record.maintenance_type == 'preventive':
                        rec.is_maintenance = True

    @api.depends("is_lease")
    def _compute_asset_lease_count(self):
        for rec in self:
            leased_rec = self.env['asset.lease'].search([('asset_id', '=', rec.id)])
            print(leased_rec)
            rec.asset_lease_count = len(leased_rec)

    @api.constrains('original_value')
    def _check_original_value(self):
        """Check original value"""
        if self.original_value and self.original_value <= 0:
            self.original_value = abs(self.original_value)
        elif self.original_value and self.salvage_value and round(self.salvage_value, 2) > round(
                self.original_value,
                2):
            raise UserError(_('The Salvage Value should not be Greater than the Original Value.'))

    @api.constrains('warranty_period')
    def _check_warranty_period(self):
        """Check warranty period positive number"""
        if self.warranty_period < 0:
            raise UserError(_('The Warranty period should not be a negative Value.'))

    @api.onchange('method_duration')
    def _onchange_method_duration(self):
        """Change methods duration"""
        if self.method_duration < 0:
            self.method_duration = abs(self.method_duration)

    @api.onchange('depreciating_factor')
    def _onchange_depreciating_factor(self):
        """Change depreciating factor"""
        if self.depreciating_factor and self.depreciating_factor < 0:
            self.depreciating_factor = abs(self.depreciating_factor)

    @api.onchange('depreciation_date')
    def _onchange_depreciation_date(self):
        """Change depreciating date"""
        purchase_date = self.date
        if self.depreciation_date and purchase_date and self.depreciation_date < purchase_date:
            raise UserError(
                _(f'The Asset is Purchased on {purchase_date}.The Depreciation Date should be greater than the Purchase Date'))

    @api.onchange('prorata_date')
    def _onchange_prorata_date(self):
        """Change prorata date"""
        purchase_date = self.date
        if self.prorata_date and purchase_date and self.prorata_date < purchase_date:
            raise UserError(
                _(f'The Asset is Purchased on {purchase_date}.The Prorata Date should be greater than the Purchase Date'))

    @api.onchange('insurance_start_date')
    def _onchange_insurance_start_date(self):
        """Function for checking the insurance start date"""
        if self.insurance_start_date and self.insurance_start_date < self.date:
            raise UserError(
                _(f'The Asset is Purchased on {self.date}. The insurance start date should be greater than the Purchase Date'))

    @api.onchange('salvage_value')
    def _onchange_salvage_value(self):
        """Change salvage value"""
        if self.salvage_value:
            if self.salvage_value < 0:
                self.salvage_value = abs(self.salvage_value)
            elif round(self.salvage_value, 2) > round(self.original_value, 2):
                raise UserError(
                    _('The Salvage Value should not be Greater than the Original Value.'))

    @api.onchange('day_amount', 'week_amount', 'month_amount', 'year_amount')
    def _onchange_day_amount(self):
        """Change day amount"""
        if (self.day_amount and self.day_amount <= 0) or (
                self.month_amount and self.month_amount <= 0) or (
                self.week_amount and self.week_amount <= 0) or (
                self.year_amount and self.year_amount <= 0):
            raise UserError(_('The value for the rental amount should be an Integer'))

    @api.onchange('fixed_asset_account_id')
    def _onchange_fixed_asset_account_id(self):
        """Function for setting the depreciation account based on fixed asset account

        Skipped when the selected asset item supplies its own accumulated
        depreciation account, otherwise the cascade that runs after
        ``_onchange_asset_item`` would overwrite it with the fixed asset
        account and every entry would credit Fixed Assets directly.
        """
        if self.asset_item_id.asset_depreciation_account_id:
            return
        self.asset_depreciation_account_id = self.fixed_asset_account_id

    @api.onchange('asset_expense_account_id')
    def _onchange_asset_expense_account_id(self):
        """Function for setting the loss account based on expense account

        Skipped when the selected asset item supplies its own loss account,
        for the same reason as ``_onchange_fixed_asset_account_id``.
        """
        if self.asset_item_id.asset_loss_account_id:
            return
        self.asset_loss_account_id = self.asset_expense_account_id

    @api.onchange('asset_item_id')
    def _onchange_asset_item(self):
        if self.asset_item_id:
            for record in self:
                if record.asset_item_id:
                    record.computation_method = record.asset_item_id.computation_method or record.computation_method
                    record.depreciation_method = record.asset_item_id.depreciation_method or record.depreciation_method
                    record.method_duration = record.asset_item_id.method_duration
                    record.brand_id = record.asset_item_id.brand_id
                    record.is_auto_calculate = record.asset_item_id.is_auto_calculate
                    record.depreciating_factor = record.asset_item_id.depreciating_factor
                    record.duration_period = record.asset_item_id.duration_period
                    record.fixed_asset_account_id = record.asset_item_id.fixed_asset_account_id
                    record.asset_depreciation_account_id = record.asset_item_id.asset_depreciation_account_id
                    record.asset_expense_account_id = record.asset_item_id.asset_expense_account_id
                    record.asset_loss_account_id = record.asset_item_id.asset_loss_account_id
                    record.asset_journal_id = record.asset_item_id.asset_journal_id
                    record.date = record.asset_item_id.date
                    record.prorata_date = record.asset_item_id.prorata_date
                    record.vendor_id = record.asset_item_id.vendor_id
                    record.automatic_maintenance = record.asset_item_id.automatic_maintenance

    def unlink(self):
        """Function for the unlink the asset"""
        for rec in self:
            if rec.status == 'running':
                raise UserError(_('You cannot delete the record that is in Running state.'))
            elif rec.is_assign or rec.is_lease or rec.is_rental or rec.is_repair or rec.is_maintenance or rec.is_reserve:
                raise UserError(
                    _('You cannot delete the record, The related asset is already taken for some '
                      'operations'))
            else:
                return super().unlink()

    def action_request_assets(self):
        """Action request assets"""
        states = ['sell', 'disposed', 'cancel']
        if self.status in states:
            asset_state = self.status
            raise UserError(_(
                f'The asset is in {asset_state}.'))
        else:
            return {
                'name': _('Request'),
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'type': 'ir.actions.act_window',
                'target': 'new'
            }

    def action_reserve_assets(self):
        """Action reserve assets"""
        states = ['sell', 'disposed', 'cancel', 'rented', 'reserved', 'leased']
        if self.status in states:
            raise UserError(
                _(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.is_reserve or self.is_assign or self.is_lease or self.is_repair or self.is_rental:
            raise UserError(
                _('You cannot complete this operation, The related asset is already taken for a another '
                  'operation'))
        else:
            return {
                'name': _('Reservation'),
                'view_mode': 'form',
                'view_id': self.env.ref('cyllo_asset_management.view_asset_reservation_form2').id,
                'res_model': 'asset.reservation',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_id': self.id,
                },
                'target': 'new'
            }

    def action_assign_assets(self):
        """Action assign assets"""
        states = ['sell', 'disposed', 'cancel', 'rented', 'reserved', 'leased']
        if self.status in states:
            raise UserError(
                _(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.is_assign or self.is_lease or self.is_repair or self.is_rental:
            raise UserError(
                _('You cannot complete this operation, The related asset is already taken for a another '
                  'operation'))
        else:
            reserved_asset = self.env['asset.reservation'].search(
                [('asset_id', '=', self.id), ('status', '=', 'reserve')])
            return {
                'name': _('Assign'),
                'view_mode': 'form',
                'view_id': self.env.ref('cyllo_asset_management.view_asset_assign_form2').id,
                'res_model': 'asset.assign',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_id': self.id,
                    'default_employee_id': reserved_asset.employee_id.id if reserved_asset else '',
                },
                'target': 'new'
            }

    def action_lease_assets(self):
        """Action lease assets"""
        states = ['sell', 'disposed', 'cancel', 'rented', 'leased']
        if not self.is_lease_asset:
            raise UserError(
                _('You cannot complete this operation, The related asset is not a lease asset.'))
        elif self.status in states:
            raise UserError(
                _(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.is_assign or self.is_lease or self.is_repair or self.is_rental:
            raise UserError(
                _('You cannot complete this operation, The related asset is already taken for a another '
                  'operation'))
        else:
            reserved_asset = self.env['asset.reservation'].search(
                [('asset_id', '=', self.id), ('status', '=', 'reserve')])
            return {
                'name': _('Lease'),
                'view_mode': 'form',
                'view_id': self.env.ref('cyllo_asset_management.view_asset_lease_form2').id,
                'res_model': 'asset.lease',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_id': self.id,
                    'default_customer_id': reserved_asset.employee_id.work_contact_id.id if reserved_asset else '',
                },
                'target': 'new'
            }

    def action_rent_assets(self):
        """Action rent assets"""
        states = ['sell', 'disposed', 'cancel', 'rented', 'leased']
        if not self.is_rental_asset:
            raise UserError(
                _('You cannot complete this operation, The related asset is not a rental asset.'))
        elif self.status in states:
            raise UserError(
                _(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.is_assign or self.is_lease or self.is_rental:
            raise UserError(
                _('You cannot complete this operation, The related asset is already taken for a another '
                  'operation'))
        else:
            reserved_asset = self.env['asset.reservation'].search(
                [('asset_id', '=', self.id), ('status', '=', 'reserve')])
            return {
                'name': _('Rental'),
                'view_mode': 'form',
                'view_id': self.env.ref('cyllo_asset_management.view_asset_rental_form2').id,
                'res_model': 'asset.rental',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_id': self.id,
                    'default_customer_id': reserved_asset.employee_id.work_contact_id.id if reserved_asset else '',
                },
                'target': 'new'
            }

    def action_maintenance_repair_assets(self):
        """Action repair or maintenance assets"""
        states = ['sell', 'disposed', 'cancel', 'rented', 'leased']
        if self.status in states:
            raise UserError(
                _(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.is_repair or self.is_maintenance:
            raise UserError(
                _('You cannot complete this operation, The related asset is already taken for a another '
                  'operation'))
        else:
            return {
                'name': _('Maintenance/Repair'),
                'view_mode': 'form',
                'res_model': 'maintenance.request',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_id': self.id,
                },
                'target': 'new'
            }

    def action_lost_missing_assets(self):
        """Action lost missing assets"""
        states = ['sell', 'disposed', 'damaged', 'cancel', 'lost', 'rented', 'reserved', 'leased']
        if self.status in states:
            raise UserError(
                _(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.depreciated_entry_ids.filtered(
                lambda x: x.state == 'posted' and x.date > Date.today()):
            raise UserError(
                _('Reverse the depreciation entries posted in the future in order to modify the depreciation.'))
        elif self.is_repair or self.is_maintenance:
            raise UserError(
                _('You cannot complete this operation, The related asset is already taken for a another '
                  'operation'))
        elif self.is_entry:
            draft_entry = self.depreciated_entry_ids.filtered(
                lambda e: e.state == 'draft')
            if not draft_entry:
                posted = True
            else:
                posted = False
            return {
                'name': _('Lost'),
                'view_mode': 'form',
                'res_model': 'asset.sell.dispose',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_asset_id': self.id,
                    'default_asset_action': 'dispose',
                    'default_disposal_type': 'lost'
                },
                'target': 'new'
            }
        else:
            self.status = 'disposed'

    def action_sell_dispose_assets(self):
        """Action sell dispose assets"""
        states = ['sell', 'disposed', 'cancel', 'rented', 'assigned', 'reserved', 'leased']
        if self.status in states:
            raise UserError(
                _(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.depreciated_entry_ids.filtered(
                lambda x: x.state == 'posted' and x.date > Date.today()):
            raise UserError(
                _('Reverse the depreciation entries posted in the future in order to modify the depreciation.'))
        elif self.is_repair or self.is_maintenance:
            raise UserError(
                _('You cannot complete this operation, The related asset is already taken for a another '
                  'operation'))
        else:
            draft_entry = self.depreciated_entry_ids.filtered(
                lambda e: e.state == 'draft')
            if not draft_entry:
                posted = True
            else:
                posted = False
            return {
                'name': _('Sell/Dispose'),
                'view_mode': 'form',
                'res_model': 'asset.sell.dispose',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_asset_id': self.id,
                    'default_is_posted': posted
                },
                'target': 'new'
            }

    def action_view_reservation(self):
        """Action view reservation"""
        reserved_asset = self.env['asset.reservation'].search([('asset_id', '=', self.id),
                                                               ('status', 'not in',
                                                                ['draft', 'cancel'])])
        return {
            'name': 'Reservation',
            'view_mode': 'list,form',
            'res_model': 'asset.reservation',
            'type': 'ir.actions.act_window',
            'domain' : [
                ('id', 'in', reserved_asset.ids)
            ]
        }

    def action_view_lease(self):
        """Action view lease"""
        leased_asset = self.env['asset.lease'].search(
            [('asset_id', '=', self.id), ('status', '=', 'lease')])
        return {
            'name': 'Lease',
            'view_mode': 'list,form',
            'res_model': 'asset.lease',
            'type': 'ir.actions.act_window',
            'domain': [['id','in', leased_asset.ids]],
            'target': 'current',
        }

    def action_view_rental(self):
        """Action view rental"""
        rental_asset = self.env['asset.rental'].search(
            [('asset_id', '=', self.id), ('status', '=', 'rent')])
        return {
            'name': 'Rental',
            'view_mode': 'list,form',
            'res_model': 'asset.rental',
            'domain': [['id', 'in', rental_asset.ids]],
            'type': 'ir.actions.act_window',
        }

    def action_view_maintenance_repairs(self):
        """Action view maintenance / repair"""
        return {
            'name': _('Maintenance / Repair'),
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request',
            'view_mode': 'tree,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {
                'default_asset_id': self.id,
                'search_default_asset_id': 1,
            }
        }

    def action_view_assign(self):
        """Action view assign"""
        assigned_asset = self.env['asset.assign'].search(
            [('asset_id', '=', self.id), ('status', '=', 'assign')])
        return {
            'name': 'Assign',
            'view_mode': 'form',
            'res_id': assigned_asset.id,
            'res_model': 'asset.assign',
            'type': 'ir.actions.act_window',
            'domain': [('asset_id', '=', self.id), ('status', '=', 'assign')]
        }

    def action_view_journal_entries(self):
        """Action view journal entries"""
        return {
            'name': 'Journal Entries',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('asset_asset_id', '=', self.id)]
        }

    def action_view_asset_booking(self):
        """Action view asset bookings"""
        return {
            'name': 'Bookings',
            'view_mode': 'tree,form',
            'res_model': 'asset.booking',
            'type': 'ir.actions.act_window',
            'domain': [('asset_id', '=', self.id)],
            'search_view_id': self.env.ref(
                'cyllo_asset_management.view_asset_booking_search_default_filter').id,
            'context': {
                'search_default_draft_bookings': 1
            },
        }

    def action_compute_depreciation(self):
        """Action compute depreciation"""
        self.depreciation_line_ids = [fields.Command.clear()]
        if self.salvage_value <= 0:
            self.is_depreciate = False
            return
        if self.original_value == 0:
            self.is_depreciate = False
            self.salvage_value = self.original_value
            return self
        self.pre_salvage_value = self.salvage_value
        if not self.depreciating_factor:
            self.is_auto_calculate = True
        if self.computation_method != 'no_prorata':
            depreciation_date = self.prorata_date
        elif self.duration_period == 'month':
            # A month based duration is counted from the month of the
            # depreciation date, not from the start of the fiscal year.
            depreciation_date = self.depreciation_date.replace(day=1)
        else:
            depreciation_date = self.company_id.compute_fiscalyear_dates(
                self.depreciation_date).get('date_from')
        calculate_value = abs(self.salvage_value)
        depreciation_duration = 0
        start_date = depreciation_date.replace(day=1)
        if self.duration_period == 'year':
            end_date = start_date + relativedelta(years=self.method_duration)
            total_depreciation_days = (end_date - start_date).days
        else:
            end_date = start_date + relativedelta(months=self.method_duration)
            total_depreciation_days = (end_date - start_date).days
        self.calculate_depreciation(calculate_value, depreciation_duration, depreciation_date,
                                    total_depreciation_days)

    def action_confirm_deprecation(self):
        """Button action for the depreciating the asset"""
        if self.original_value == 0:
            raise UserError(_('The Original Value should be Greater than 0.'))
        if self.salvage_value > 0 and self.method_duration <= 0:
            raise UserError(
                _('Duration must be greater than zero when Salvage Value is greater than zero.'))
        self.action_compute_depreciation()
        self._create_journal_entries()
        self.status = 'running'
        self.is_confirm = True

    def action_cancel_asset(self):
        """Button action for the cancelling the asset"""
        if self.is_reserve or self.is_assign or self.is_lease or self.is_rental or self.is_repair or self.is_maintenance:
            return {
                'name': 'Assets Cancel warning',
                'view_mode': 'form',
                'res_model': 'asset.cancel.warning',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_id': self.id,
                },
                'target': 'new'
            }
        elif self.depreciated_entry_ids:
            self.depreciated_entry_ids.filtered(lambda d: d.state == 'draft').unlink()
            self.status = 'cancel'
        else:
            self.status = 'cancel'

    def action_modify_asset(self):
        """Button action for the modifying the asset"""
        self.is_revaluate = False
        if self.depreciated_entry_ids.filtered(
                lambda x: x.state == 'posted' and x.date > Date.today()):
            raise UserError(
                _('Reverse the depreciation entries posted in the future in order to modify the depreciation.'))
        else:
            return {
                'name': _('Modify Asset'),
                'view_mode': 'form',
                'res_model': 'asset.modify',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_asset_asset_id': self.id,
                    'default_asset_journal_id': self.asset_journal_id.id,
                    'default_fixed_asset_account_id': self.fixed_asset_account_id.id,
                    'default_asset_depreciation_account_id': self.asset_depreciation_account_id.id,
                    'default_asset_expense_account_id': self.asset_expense_account_id.id,
                    'default_salvage_value': self.salvage_value,
                    'default_depreciation_method': self.depreciation_method,
                    'default_duration_period': self.duration_period,
                    'default_method_duration': self.method_duration,
                    'default_depreciation_date': self.depreciation_date,
                }
            }

    def action_revaluate_asset(self):
        """Button action for revaluating the asset"""
        if self.salvage_value > self.original_value:
            raise UserError(_('The depreciable value cannot be greater than the original value.'))
        if self.salvage_value < 0:
            raise UserError(_('The depreciable value cannot be negative.'))
        if self.salvage_value > 0 and self.method_duration <= 0:
            raise UserError(_('Duration must be greater than zero when the '
                              'depreciable value is greater than zero.'))

        posted_entries = self.depreciated_entry_ids.filtered(
            lambda e: e.state == 'posted' and not e.reversal_move_id and not e.reversed_entry_id)
        draft_entries = self.depreciated_entry_ids.filtered(lambda e: e.state == 'draft')

        # We need to unlink draft entries and their associated depreciation lines.
        # But we also need to keep the ones linked to posted entries.
        draft_lines = self.depreciation_line_ids.filtered(
            lambda l: not l.journal_reference or l.journal_reference.state == 'draft')
        draft_lines.unlink()
        draft_entries.unlink()

        # The amount already depreciated
        posted_amount = sum(posted_entries.mapped('amount_total_signed'))
        current_salvage = self.salvage_value - posted_amount

        depreciation_duration = len(posted_entries) + 1

        if self.salvage_value <= posted_amount:
            # Fully depreciated or decreased beyond posted amount
            self.is_modify = False
            self.is_confirm = True
            return

        # Determine start date for the next line
        if posted_entries:
            last_posted_date = max(posted_entries.mapped('date'))
            if self.duration_period == 'month':
                depreciation_date = last_posted_date + relativedelta(months=1)
                depreciation_date = depreciation_date.replace(day=1)
            else:
                depreciation_date = last_posted_date + relativedelta(years=1)
                # Need to match fiscal year start if necessary, but standard odoo usually shifts
        else:
            depreciation_date = self.depreciation_date

        total_depreciation_days = 0
        if self.computation_method == 'daily_compute':
            start_date = depreciation_date.replace(day=1)
            if self.duration_period == 'year':
                end_date = start_date + relativedelta(years=self.method_duration)
            else:
                end_date = start_date + relativedelta(months=self.method_duration)
            total_depreciation_days = (end_date - start_date).days

        # Call calculation passing initial values so it resumes correctly
        self.calculate_depreciation(self.salvage_value, depreciation_duration, depreciation_date,
                                    total_depreciation_days, initial_previous_amount=posted_amount,
                                    initial_salvage=current_salvage)
        self._create_journal_entries()

        self.is_modify = False
        self.is_confirm = True

    def action_reset_to_draft(self):
        """Button action for the reset the asset in to the draft state"""
        self.salvage_value = self.original_value
        if self.depreciated_entry_ids:
            self.depreciated_entry_ids.filtered(
                lambda e: e.state in ('posted', 'cancel')).button_draft()
            self.depreciated_entry_ids.filtered(lambda d: d.state == 'draft').unlink()
        if self.modified_asset_ids:
            self.modified_asset_ids.unlink()
        self.depreciation_line_ids.unlink()
        self.status = 'draft'
        self.is_depreciate = False
        self.is_entry = False
        self.is_modify = False
        self.is_confirm = False
        self.is_reserve = False
        self.is_assign = False
        self.is_lease = False
        self.is_rental = False
        self.is_repair = False
        self.is_maintenance = False
        self.is_sell = False
        self.is_dispose = False
        self.is_lost = False
        self.modify_value = 0
        self.is_revaluate = False
        self.is_decrease_value = False

    def action_view_modified_asset(self):
        """Function for the viewing the modified asset"""
        return {
            'name': 'Asset',
            'view_mode': 'tree,form',
            'res_model': 'asset.asset',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.modified_asset_ids.ids)]
        }

    def _get_depreciating_factor(self, calculate_value):
        """Depreciating factor"""
        depreciating_factor = 0
        if self.is_auto_calculate:
            declining_factor = round(calculate_value / self.method_duration, 2)
            factor = round(declining_factor / calculate_value, 2)
            if self.depreciation_method in ['declining_balance', 'declining_straight_line']:
                depreciating_factor = round(factor, 2)
        else:
            if self.depreciation_method in ['declining_balance', 'declining_straight_line']:
                depreciating_factor = self.depreciating_factor
        return depreciating_factor

    def _compute_no_prorata_depreciation_amount(self, calculate_value, salvage_value, year,
                                                depreciating_factor,
                                                depreciation_days, balancing_value,
                                                depreciate_value):
        """Compute no prorata depreciation amount"""
        if self.depreciation_method == 'straight_line':
            amount = calculate_value / self.method_duration
            if year == self.method_duration:
                amount = salvage_value
        elif self.depreciation_method == 'declining_straight_line':
            if self.duration_period == 'month':
                amount = calculate_value / self.method_duration
            else:
                if year == 1:
                    amount = depreciating_factor * calculate_value
                elif year == self.method_duration:
                    amount = salvage_value
                else:
                    amount = salvage_value * depreciating_factor
        else:
            depreciate_amount = round(depreciating_factor * salvage_value / 12, 2)
            if year == self.method_duration + balancing_value:
                amount = salvage_value
            else:
                amount = depreciating_factor * salvage_value if self.duration_period == 'year' else depreciate_amount
        return amount

    def _compute_constant_period_depreciation_amount(self, calculate_value, salvage_value, year,
                                                     depreciation_date,
                                                     balance_month, balancing_value,
                                                     depreciate_value,
                                                     depreciating_factor, total_depreciation_days,
                                                     depreciation_days,
                                                     depreciation_duration):
        """Compute constant period depreciation amount"""
        day_count = 366 if calendar.isleap(depreciation_date.year) else 365
        days_in_month = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
        if self.depreciation_method == 'straight_line':
            if not self.is_revaluate:
                straight_line_value = calculate_value / self.method_duration
                depreciation_days = (days_in_month - depreciation_date.day) + 1
                if year == 1:
                    year_amount = straight_line_value
                    month_amount = year_amount / 12
                    day_amount = month_amount / days_in_month
                    current_month_depreciation = depreciation_days * day_amount
                    amount = ((
                                      balance_month * month_amount) + current_month_depreciation) if self.duration_period == 'year' else (
                            (year_amount / days_in_month) * depreciation_days)
                elif year == self.method_duration + balancing_value:
                    amount = salvage_value
                else:
                    amount = straight_line_value
            else:
                day_value = calculate_value / total_depreciation_days
                amount = day_value * depreciation_days

        elif self.depreciation_method == 'declining_straight_line':
            if not self.is_revaluate:
                if self.duration_period == 'month':
                    amount = round((depreciating_factor * salvage_value / 12) * (
                            days_in_month - depreciation_date.day + 1) / days_in_month, 2)
                else:
                    if year == 1:
                        day_amount = depreciate_value / day_count
                        amount = day_amount * depreciation_days
                    elif year == self.method_duration + balancing_value:
                        amount = salvage_value
                    else:
                        amount = depreciating_factor * salvage_value
            else:
                day_value = calculate_value / total_depreciation_days
                amount = day_value * depreciation_days
        else:
            depreciate_amount = round(depreciating_factor * salvage_value / 12, 2)
            if not self.is_revaluate or self.is_decrease_value:
                if year == 1:
                    day_amount = depreciate_value / day_count
                    amount = day_amount * depreciation_days if self.duration_period == 'year' else depreciate_amount * depreciation_days / days_in_month
                elif year == self.method_duration + balancing_value:
                    amount = salvage_value
                else:
                    amount = depreciating_factor * salvage_value if self.duration_period == 'year' else depreciate_amount
            else:
                if year == self.method_duration + balancing_value:
                    amount = salvage_value
                else:
                    amount = depreciating_factor * salvage_value
        return amount

    def _compute_daily_compute_depreciation_amount(self, calculate_value, salvage_value, year,
                                                   year_end_depreciation,
                                                   depreciation_date, total_depreciation_days,
                                                   depreciation_days, balancing_value,
                                                   depreciating_factor):
        """Compute daily depreciation amount"""
        total_days = (year_end_depreciation - depreciation_date).days + 1
        total_month_days = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
        day_count = 366 if calendar.isleap(depreciation_date.year) else 365
        depreciate_value = depreciating_factor * salvage_value
        year_amount = depreciate_value / day_count

        day_amount = calculate_value / total_depreciation_days
        if self.depreciation_method == 'straight_line':
            if year == 1:
                amount = day_amount * total_days if self.duration_period == 'year' else day_amount * depreciation_days
            elif year == self.method_duration + balancing_value:
                amount = salvage_value
            else:
                amount = day_amount * day_count if self.duration_period == 'year' else day_amount * total_month_days
        elif self.depreciation_method == 'declining_straight_line':
            if year == 1:
                amount = year_amount * total_days if self.duration_period == 'year' else day_amount * depreciation_days
            elif year == self.method_duration + balancing_value:
                amount = depreciate_value * day_count if self.duration_period == 'year' else salvage_value
            else:
                amount = depreciate_value if self.duration_period == 'year' else day_amount * depreciation_days
        else:
            if year == 1:
                amount = round(year_amount * total_days,
                               2) if self.duration_period == 'year' else round(
                    year_amount * depreciation_days, 2)
            elif year == self.method_duration + balancing_value:
                amount = salvage_value
            else:
                amount = salvage_value * depreciating_factor if self.duration_period == 'year' else round(
                    year_amount * total_month_days, 2)
        return amount

    def _create_depreciation_lines(self, calculate_value, amount, year, year_end_depreciation,
                                   month_end_depreciation,
                                   previous_amount, salvage_value, depreciating_factor,
                                   balancing_value):
        """Creating depreciation lines"""
        depreciate_value = 0
        if self.is_decrease_value:
            previous_amount = math.ceil(self.depreciation_line_ids.filtered(
                lambda record: record.id == max(
                    self.depreciation_line_ids.ids)).accumulative_depreciation + amount)
            salvage_value = self.depreciation_line_ids.filtered(
                lambda record: record.id == max(
                    self.depreciation_line_ids.ids)).salvage_value - amount
            if self.method_duration + balancing_value == year:
                self.is_decrease_value = False
                previous_amount -= amount
                amount = salvage_value + amount
                calculate_value = previous_amount + amount
                calculate_value = calculate_value if calculate_value == self.pre_salvage_value else self.pre_salvage_value
                previous_amount = calculate_value
                salvage_value = 0
        else:
            depreciate_value = depreciating_factor * calculate_value
        accumulated = calculate_value if depreciate_value > calculate_value or previous_amount > calculate_value and not self.is_decrease_value else previous_amount
        vals = [fields.Command.create({
            'depreciation_expense': calculate_value if depreciate_value > calculate_value else amount,
            'depreciation_id': self.id,
            'date': year_end_depreciation if self.duration_period == 'year' else month_end_depreciation,
            'accumulative_depreciation': accumulated,
            # Book value runs down from the original value, so it stops at the
            # non depreciable remainder instead of always reaching zero.
            'salvage_value': self.original_value - accumulated,
        })]
        self.write({'depreciation_line_ids': vals})

    def _create_journal_entries(self):
        """Create journal entries"""
        for depreciation in self.depreciation_line_ids:
            if not depreciation.journal_reference:
                move_lines = []
                move_lines.append({
                    'name': self.name,
                    'account_id': self.asset_depreciation_account_id.id,
                    'credit': depreciation.depreciation_expense,
                    'debit': 0.0,
                    'currency_id': self.currency_id.id,
                })
                move_lines.append({
                    'name': self.name,
                    'account_id': self.asset_expense_account_id.id,
                    'debit': depreciation.depreciation_expense,
                    'credit': 0.0,
                    'currency_id': self.currency_id.id,
                })
                vals = {
                    'move_type': 'entry',
                    'asset_asset_id': self.id,
                    'ref': _("%s: Depreciation", self.name),
                    'date': depreciation.date,
                    'invoice_date_due': depreciation.date,
                    'journal_id': self.asset_journal_id.id,
                    'auto_post': 'at_date',
                    'depreciation_line_id': depreciation.id,
                    'line_ids': [fields.Command.create(lines) for lines in move_lines],
                }
                journal_items = self.env['account.move'].create(vals)
                depreciation.journal_reference = journal_items.id
                past_journals = journal_items.filtered(
                    lambda x: x.invoice_date_due <= fields.date.today())

                if past_journals:
                    past_journals._post()

    def calculate_depreciation(self, calculate_value, depreciation_duration, depreciation_date,
                               total_depreciation_days, initial_previous_amount=0,
                               initial_salvage=None):
        """Calculation depreciation values"""
        self.is_depreciate = True
        self.is_entry = True
        depreciating_factor = self._get_depreciating_factor(calculate_value)
        depreciate_value = calculate_value * depreciating_factor
        year_end_depreciation = self.company_id.compute_fiscalyear_dates(depreciation_date).get(
            'date_to')
        month_end_depreciation = end_of(depreciation_date, granularity='month')
        if self.duration_period == 'month':
            depreciation_days = (month_end_depreciation - depreciation_date).days + 1
        else:
            depreciation_days = (year_end_depreciation - depreciation_date).days + 1
        pending_days = total_depreciation_days
        balance_month = year_end_depreciation.month - depreciation_date.month
        salvage_value = initial_salvage if initial_salvage is not None else calculate_value
        previous_amount = initial_previous_amount
        balancing_value = 0 if self.computation_method == 'no_prorata' else 1
        for period in range(self.method_duration + balancing_value):
            year = period + 1
            if year >= depreciation_duration:
                amount = 0
                if self.computation_method == 'no_prorata':
                    amount = self._compute_no_prorata_depreciation_amount(calculate_value,
                                                                          salvage_value, year,
                                                                          depreciating_factor,
                                                                          depreciation_days,
                                                                          balancing_value,
                                                                          depreciate_value)
                    straight_line_value = salvage_value / (
                                self.method_duration - year + balancing_value) if self.method_duration + balancing_value != year else salvage_value
                    if self.depreciation_method == 'declining_straight_line' and amount <= straight_line_value:
                        amount = straight_line_value
                        self._calculate_declining_straight_line(amount, previous_amount,
                                                                salvage_value, calculate_value,
                                                                year_end_depreciation,
                                                                month_end_depreciation,
                                                                year, balancing_value)
                        break
                    previous_amount = amount if year == 1 else previous_amount + amount
                    salvage_value = salvage_value - amount if year > 1 else calculate_value - amount

                if self.computation_method == 'constant_period':
                    amount = self._compute_constant_period_depreciation_amount(calculate_value,
                                                                               salvage_value, year,
                                                                               depreciation_date,
                                                                               balance_month,
                                                                               balancing_value,
                                                                               depreciate_value,
                                                                               depreciating_factor,
                                                                               total_depreciation_days,
                                                                               depreciation_days,
                                                                               depreciation_duration)
                    straight_line_value = salvage_value / (
                                self.method_duration - year + balancing_value) if self.method_duration + balancing_value != year else salvage_value
                    if self.depreciation_method == 'declining_straight_line' and amount <= straight_line_value and year != 1:
                        amount = straight_line_value
                        self._calculate_declining_straight_line(amount, previous_amount,
                                                                salvage_value,
                                                                calculate_value,
                                                                year_end_depreciation,
                                                                month_end_depreciation,
                                                                year, balancing_value)
                        break
                    previous_amount = amount if year == 1 else previous_amount + amount
                    salvage_value = salvage_value - amount if year > 1 else calculate_value - amount
                if self.computation_method == 'daily_compute':
                    amount = self._compute_daily_compute_depreciation_amount(calculate_value,
                                                                             salvage_value, year,
                                                                             year_end_depreciation,
                                                                             depreciation_date,
                                                                             total_depreciation_days,
                                                                             depreciation_days,
                                                                             balancing_value,
                                                                             depreciating_factor)
                    straight_line_value = salvage_value / pending_days * depreciation_days
                    if self.depreciation_method == 'declining_straight_line' and amount <= straight_line_value and self.duration_period == 'year' and year != 1:
                        amount = straight_line_value
                        self._calculate_declining_straight_line(amount, previous_amount,
                                                                salvage_value,
                                                                calculate_value,
                                                                year_end_depreciation,
                                                                month_end_depreciation,
                                                                year, balancing_value)
                        break
                    previous_amount = amount if year == 1 else previous_amount + amount
                    salvage_value = calculate_value - amount if year == 1 else salvage_value - amount
                self._create_depreciation_lines(calculate_value, amount, year,
                                                year_end_depreciation,
                                                month_end_depreciation, previous_amount,
                                                salvage_value,
                                                depreciating_factor, balancing_value)

                if (depreciating_factor * calculate_value > calculate_value) or (
                        round(previous_amount, 2) >= calculate_value):
                    break
                pending_days = max(0, pending_days - depreciation_days)
                if self.duration_period == 'month':
                    depreciation_date = month_end_depreciation + relativedelta(months=1)
                    month_end_depreciation = end_of(depreciation_date, granularity='month')
                    depreciation_days = 30 if self.computation_method == 'constant_period' else \
                        calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                else:
                    depreciation_date = year_end_depreciation + relativedelta(years=1)
                    year_end_depreciation = end_of(depreciation_date, granularity='year')
                    depreciation_days = 366 if calendar.isleap(depreciation_date.year) else 365

    def _calculate_declining_straight_line(self, amount, previous_amount, salvage_value,
                                           calculate_value,
                                           year_end_depreciation, month_end_depreciation,
                                           year, balancing_value):
        """Calculation depreciation values for declining straight line method"""
        year_count = (self.method_duration + balancing_value) - (year - 1) if year > 1 else (
                self.method_duration + balancing_value)
        for count in range(year_count):
            accumulated = previous_amount + salvage_value if salvage_value < amount else previous_amount + amount
            vals = [fields.Command.create({
                'depreciation_expense': salvage_value if salvage_value < amount else amount,
                'depreciation_id': self.id,
                'year': year,
                'date': year_end_depreciation if self.duration_period == 'year' else month_end_depreciation,
                'accumulative_depreciation': accumulated,
                'salvage_value': self.original_value - accumulated,
            })]

            if self.duration_period == 'month':
                depreciation_date = month_end_depreciation + relativedelta(months=1)
                month_end_depreciation = end_of(depreciation_date, granularity='month')

            else:
                depreciation_date = year_end_depreciation + relativedelta(years=1)
                year_end_depreciation = end_of(depreciation_date, granularity='year')

            self.write({'depreciation_line_ids': vals})
            year = year + 1
            previous_amount = previous_amount + amount
            salvage_value = salvage_value - amount
            if (amount > calculate_value) or (round(previous_amount, 2) >= calculate_value):
                break

    def create_modify_asset(self, calculate_value, depreciation_duration, depreciation_date,
                            total_depreciation_days):
        """Function for creating modified asset"""
        self.modify_value = abs(calculate_value)
        if self.modify_value < 0:
            raise UserError(
                _('You cannot create an asset from lines containing credit and debit on the account or with a null amount'))
        vals = {
            'name': _("%s: %s", self.reference_note, self.name),
            'parent_id': self.id,
            'method_duration': self.method_duration,
            'duration_period': self.duration_period,
            'asset_item_id': self.asset_item_id.id,
            'asset_journal_id': self.asset_journal_id.id,
            'fixed_asset_account_id': self.fixed_asset_account_id.id,
            'asset_depreciation_account_id': self.asset_depreciation_account_id.id,
            'asset_expense_account_id': self.asset_expense_account_id.id,
            'asset_loss_account_id': self.asset_loss_account_id.id,
            'company_id': self.company_id.id,
            'date': self.date,
            'status': 'running',
            'brand_id': self.brand_id,
            'original_value': calculate_value,
            'salvage_value': calculate_value,
            'depreciation_method': self.depreciation_method,
            'depreciation_date': self.depreciation_date,
            'computation_method': 'constant_period',
            'prorata_date': depreciation_date,
            'is_auto_calculate': self.is_auto_calculate if self.is_auto_calculate else False,
            'depreciating_factor': self.depreciating_factor if self.depreciating_factor else False,
        }
        modified_asset = self.env['asset.asset'].sudo().create(vals)
        self.modified_asset_ids = [fields.Command.link(modified_asset.id)]
        modified_asset.is_revaluate = True
        modified_asset.calculate_depreciation(calculate_value, depreciation_duration,
                                              depreciation_date,
                                              total_depreciation_days)
        modified_asset._create_journal_entries()
        modified_asset.is_confirm = True
        total_value = sum(
            self.depreciated_entry_ids.filtered(lambda a: a.state == 'draft').mapped(
                'amount_total_signed'))
        total_value += sum(
            self.modified_asset_ids.filtered(lambda a: a.status == 'running').mapped(
                'salvage_value'))
        self.salvage_value = total_value

    @api.onchange('automatic_maintenance')
    def on_automatic_maintenance(self):
        today = fields.date.today()
        if self.automatic_maintenance != 'no':
            self.last_maintenance_date = today

    @api.depends("last_maintenance_date", "automatic_maintenance")
    def compute_next_maintenance_date(self):
        for rec in self:
            if rec.last_maintenance_date and self.automatic_maintenance != 'no':
                if rec.automatic_maintenance == 'weekly':
                    rec.next_maintenance_date = rec.last_maintenance_date + relativedelta(weeks=1)
                elif rec.automatic_maintenance == 'monthly':
                    rec.next_maintenance_date = rec.last_maintenance_date + relativedelta(months=1)
                elif rec.automatic_maintenance == 'quarterly':
                    rec.next_maintenance_date = rec.last_maintenance_date + relativedelta(months=3)
                elif rec.automatic_maintenance == 'semi_annually':
                    rec.next_maintenance_date = rec.last_maintenance_date + relativedelta(months=6)
                elif rec.automatic_maintenance == 'yearly':
                    rec.next_maintenance_date = rec.last_maintenance_date + relativedelta(years=1)

    @api.model
    def _cron_generate_maintenance_requests(self):
        """Cron job to automatically generate maintenance requests based on frequency."""
        today = fields.date.today()
        assets = self.search([('automatic_maintenance', '!=', 'no')])
        assets.filtered(lambda asset: asset.next_maintenance_date == today)

        for asset in assets:
            self.env['maintenance.request'].create({
                'name': f"Auto Maintenance - {asset.name}",
                'asset_id': asset.id,
                'maintenance_type': 'preventive',
                'schedule_date': today,
                'duration': 1,
            })

            # Advance next_maintenance_date
            if asset.automatic_maintenance == 'weekly':
                asset.last_maintenance_date = today
                asset.next_maintenance_date = today + relativedelta(weeks=1)
            elif asset.automatic_maintenance == 'monthly':
                asset.last_maintenance_date = today
                asset.next_maintenance_date = today + relativedelta(months=1)
            elif asset.automatic_maintenance == 'quarterly':
                asset.last_maintenance_date = today
                asset.next_maintenance_date = today + relativedelta(months=3)
            elif asset.automatic_maintenance == 'semi_annually':
                asset.last_maintenance_date = today
                asset.next_maintenance_date = today + relativedelta(months=6)
            elif asset.automatic_maintenance == 'yearly':
                asset.last_maintenance_date = today
                asset.next_maintenance_date = today + relativedelta(years=1)
