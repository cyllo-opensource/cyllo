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

from odoo import _, fields, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    wip_entry_count = fields.Integer(compute='_compute_wip_entry_count', string="WIP Entry Count")

    def _compute_wip_entry_count(self):
        data = self.env['account.move']._read_group(
            [('production_id', 'in', self.ids)],
            ['production_id'],
            ['__count']
        )
        count_data = {prod.id: count for prod, count in data}
        for prod in self:
            prod.wip_entry_count = count_data.get(prod.id, 0)

    def action_view_wip_entries(self):
        self.ensure_one()
        tree_view_id = self.env.ref('cyllo_wip_manufacturing.view_move_tree_wip').id
        action = {
            'name': _("WIP Entries of %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('production_id', '=', self.id)],
            'context': {
                'default_production_id': self.id,
                'default_move_type': 'entry',
            },
            'views': [
                (tree_view_id, 'tree'),
                (False, 'form'),
            ]
        }
        return action

    def action_post_wip_entries(self):
        self.ensure_one()
        if not self.company_id.wip_active:
            raise UserError(_("WIP Accounting is not enabled for this company. Please configure it in Settings."))
        return {
            'name': _('Post WIP Accounting Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.wip.accounting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_production_id': self.id,
            }
        }
