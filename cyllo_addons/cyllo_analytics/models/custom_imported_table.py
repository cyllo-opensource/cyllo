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
from odoo.tools import SQL
import logging

_logger = logging.getLogger(__name__)

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

        cr = self.env.cr
        record_id = self.id
        action_id = self.action_id.id
        model_id = self.model_id.id
        model_name = self.model_id.model
        model_state = self.model_id.state
        table_name = self.env[model_name]._table if model_name in self.env else (model_name or '').replace('.', '_')
        self.env.flush_all()

        cr.execute("DELETE FROM custom_imported_table WHERE id = %s", (record_id,))
        if action_id:
            cr.execute("DELETE FROM ir_ui_menu WHERE action = %s", (f'ir.actions.act_window,{action_id}',))
            cr.execute("DELETE FROM ir_act_window WHERE id = %s", (action_id,))
        if model_id and model_state == 'manual':
            cr.execute("DELETE FROM ir_model_access WHERE model_id = %s", (model_id,))
            cr.execute("DELETE FROM ir_model_fields WHERE model_id = %s OR relation = %s", (model_id, model_name))
            cr.execute("DELETE FROM ir_model WHERE id = %s", (model_id,))
            cr.execute(SQL("DROP TABLE IF EXISTS %s CASCADE", SQL.identifier(table_name)))

        self.env.invalidate_all()
        self.env.registry.clear_cache()
        if model_id and model_state == 'manual':
            self.env.registry.setup_models(cr)

        result = {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        return result

