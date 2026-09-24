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
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CustomImportedTable(models.Model):
    _name = 'custom.imported.table'
    _description = 'Imported Dynamic Table Registry'
    _order = 'import_date desc'

    name = fields.Char(string='Table Label', required=True)
    model_id = fields.Many2one('ir.model', string='Table Model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='Technical Name', store=True)
    import_date = fields.Datetime(string='Import Date', default=fields.Datetime.now, required=True)
    record_count = fields.Integer(string='Record Count', compute='_compute_record_count')
    action_id = fields.Many2one('ir.actions.act_window', string='Window Action', ondelete='cascade')

    def _compute_record_count(self):
        for rec in self:
            if rec.model_name and rec.model_name in self.env:
                try:
                    rec.record_count = self.env[rec.model_name].sudo().search_count([])
                except Exception:
                    rec.record_count = 0
            else:
                rec.record_count = 0

    def action_view_data(self):
        self.ensure_one()
        if not self.action_id:
            raise UserError(_("No action found for this table."))
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': self.model_name,
            'view_mode': 'tree,form',
        }

    def action_drop_table(self):
        self.ensure_one()

        action_to_delete = self.action_id
        model_to_delete = self.model_id

        # 1. Delete dependent stuff FIRST
        if model_to_delete:
            accesses = self.env['ir.model.access'].sudo().search([
                ('model_id', '=', model_to_delete.id)
            ])
            accesses.unlink()

            fields_to_del = self.env['ir.model.fields'].sudo().search([
                ('model_id', '=', model_to_delete.id),
                ('state', '=', 'manual')
            ])
            fields_to_del.unlink()

            if model_to_delete.state == 'manual':
                model_to_delete.sudo().unlink()

        self.env.flush_all()

        # 2. DELETE SELF FIRST
        self.unlink()

        # 3. RETURN ACTION (trigger basic client reload)
        result = {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

        # 4. DELETE ACTION LAST (very important)
        if action_to_delete:
            action_to_delete.sudo().unlink()

        return result

