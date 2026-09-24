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

import json
from odoo import api, fields, models


class PlmEcoCompareWizard(models.TransientModel):
    _name = 'plm.eco.compare.wizard'
    _description = 'ECO Compare Wizard'

    eco_id = fields.Many2one('plm.eco', string="ECO", required=True, ondelete='cascade')
    html_diff = fields.Html(string="Comparison Report", readonly=True)

    @api.model
    def default_get(self, fields_list):
        """ Fetch default values for the wizard, computing/loading the HTML diff snapshot if not already saved. """
        res = super(PlmEcoCompareWizard, self).default_get(fields_list)
        eco_id = self.env.context.get('active_id')
        if eco_id:
            eco = self.env['plm.eco'].browse(eco_id)
            res['eco_id'] = eco_id
            if eco.is_done_stage and eco.diff_snapshot_html:
                res['html_diff'] = eco.diff_snapshot_html
            else:
                res['html_diff'] = self._generate_html_diff(eco)
        return res

    def _generate_html_diff(self, eco):
        """ Generate an HTML representation comparing the original and revised BoM, or product templates. """
        if not eco:
            return "<h3>No ECO loaded.</h3>"

        html = []
        if eco.apply_on == 'bom':
            bom_orig = eco.original_bom_id
            bom_rev = eco.comparison_bom_id

            if not bom_orig:
                return "<div class='alert alert-warning'>Original BoM is not set.</div>"
            if not bom_rev:
                return "<div class='alert alert-warning'>Revised BoM has not been created yet. (Move ECO to 'In Progress' to create revised BoM).</div>"

            orig_lines = {line.product_id.id: line for line in bom_orig.bom_line_ids}
            rev_lines = {line.product_id.id: line for line in bom_rev.bom_line_ids}

            added_comp = []
            removed_comp = []
            modified_comp = []

            all_products = set(orig_lines.keys()) | set(rev_lines.keys())
            for prod_id in all_products:
                orig_line = orig_lines.get(prod_id)
                rev_line = rev_lines.get(prod_id)

                if orig_line and not rev_line:
                    removed_comp.append(orig_line)
                elif rev_line and not orig_line:
                    added_comp.append(rev_line)
                else:
                    if orig_line.product_qty != rev_line.product_qty or orig_line.product_uom_id != rev_line.product_uom_id:
                        modified_comp.append((orig_line, rev_line))
            orig_ops = {operation.name: operation for operation in bom_orig.operation_ids}
            rev_ops = {operation.name: operation for operation in bom_rev.operation_ids}
            added_ops = []
            removed_ops = []
            modified_ops = []

            all_ops = set(orig_ops.keys()) | set(rev_ops.keys())
            for op_name in all_ops:
                orig_operation = orig_ops.get(op_name)
                rev_operation = rev_ops.get(op_name)

                if orig_operation and not rev_operation:
                    removed_ops.append(orig_operation)
                elif rev_operation and not orig_operation:
                    added_ops.append(rev_operation)
                else:
                    if orig_operation.workcenter_id != rev_operation.workcenter_id or orig_operation.time_cycle != rev_operation.time_cycle:
                        modified_ops.append((orig_operation, rev_operation))

            html.append("<div style='font-family: sans-serif;'>")
            html.append(f"<h3 style='color: #202124; margin-bottom: 20px;'>BoM Revision Comparison</h3>")
            html.append(f"<p class='text-muted'>Comparing <b>{bom_orig.display_name} (v{bom_orig.version or '1'})</b> vs <b>{bom_rev.display_name} (v{bom_rev.version or '2'})</b></p>")

            html.append("<div class='card mb-4 shadow-sm' style='border-radius: 8px;'>")
            html.append("<div class='card-header bg-light'><b>Component Changes</b></div>")
            html.append("<div class='card-body p-0'>")
            if not added_comp and not removed_comp and not modified_comp:
                html.append("<p class='p-3 text-success mb-0'>No component changes detected.</p>")
            else:
                html.append("<table class='table table-hover mb-0'>")
                html.append("<thead class='table-light'><tr><th>Component</th><th>Change Type</th><th>Original Qty</th><th>New Qty</th></tr></thead>")
                html.append("<tbody>")
                for line in added_comp:
                    html.append(f"<tr class='table-success'><td style='font-weight: 500; color: #1e7e34;'>{line.product_id.display_name}</td><td><span class='badge bg-success'>Added</span></td><td>-</td><td>{line.product_qty} {line.product_uom_id.name}</td></tr>")
                for line in removed_comp:
                    html.append(f"<tr class='table-danger'><td style='font-weight: 500; color: #bd2130; text-decoration: line-through;'>{line.product_id.display_name}</td><td><span class='badge bg-danger'>Removed</span></td><td>{line.product_qty} {line.product_uom_id.name}</td><td>-</td></tr>")
                for orig, rev in modified_comp:
                    html.append(f"<tr class='table-warning'><td style='font-weight: 500; color: #d39e00;'>{orig.product_id.display_name}</td><td><span class='badge bg-warning text-dark'>Quantity Changed</span></td><td>{orig.product_qty} {orig.product_uom_id.name}</td><td style='font-weight: bold;'>{rev.product_qty} {rev.product_uom_id.name}</td></tr>")
                html.append("</tbody></table>")
            html.append("</div></div>")

            html.append("<div class='card mb-4 shadow-sm' style='border-radius: 8px;'>")
            html.append("<div class='card-header bg-light'><b>Operation Changes</b></div>")
            html.append("<div class='card-body p-0'>")
            if not added_ops and not removed_ops and not modified_ops:
                html.append("<p class='p-3 text-success mb-0'>No operation changes detected.</p>")
            else:
                html.append("<table class='table table-hover mb-0'>")
                html.append("<thead class='table-light'><tr><th>Operation</th><th>Change Type</th><th>Original Details</th><th>New Details</th></tr></thead>")
                html.append("<tbody>")
                for op in added_ops:
                    html.append(f"<tr class='table-success'><td style='font-weight: 500; color: #1e7e34;'>{op.name}</td><td><span class='badge bg-success'>Added</span></td><td>-</td><td>Work Center: {op.workcenter_id.name}<br/>Duration: {op.time_cycle} min</td></tr>")
                for op in removed_ops:
                    html.append(f"<tr class='table-danger'><td style='font-weight: 500; color: #bd2130; text-decoration: line-through;'>{op.name}</td><td><span class='badge bg-danger'>Removed</span></td><td>Work Center: {op.workcenter_id.name}<br/>Duration: {op.time_cycle} min</td><td>-</td></tr>")
                for orig, rev in modified_ops:
                    orig_details = []
                    rev_details = []
                    if orig.workcenter_id != rev.workcenter_id:
                        orig_details.append(f"Work Center: {orig.workcenter_id.name}")
                        rev_details.append(f"Work Center: <b>{rev.workcenter_id.name}</b> (Changed)")
                    else:
                        orig_details.append(f"Work Center: {orig.workcenter_id.name}")
                        rev_details.append(f"Work Center: {rev.workcenter_id.name}")

                    if orig.time_cycle != rev.time_cycle:
                        orig_details.append(f"Duration: {orig.time_cycle} min")
                        rev_details.append(f"Duration: <b>{rev.time_cycle} min</b> (Changed)")
                    else:
                        orig_details.append(f"Duration: {orig.time_cycle} min")
                        rev_details.append(f"Duration: {rev.time_cycle} min")

                    html.append(f"<tr class='table-warning'><td style='font-weight: 500; color: #d39e00;'>{orig.name}</td><td><span class='badge bg-warning text-dark'>Modified</span></td><td>{', '.join(orig_details)}</td><td>{', '.join(rev_details)}</td></tr>")
                html.append("</tbody></table>")
            html.append("</div></div>")
            html.append("</div>")


        elif eco.apply_on == 'product':
            product = eco.product_id
            if not product:
                return "<div class='alert alert-warning'>No product linked to this ECO.</div>"

            if not eco.product_snapshot:
                return "<div class='alert alert-info'>No snapshot available. Move ECO to In Progress to capture baseline.</div>"

            before = json.loads(eco.product_snapshot)
            after = {}
            for field_name in before.keys():
                field = product._fields.get(field_name)
                if not field:
                    continue
                try:
                    after[field_name] = eco._normalize_field_value(product[field_name])
                except Exception:
                    continue


            changes = [
                (field_name, before[field_name], after[field_name])
                for field_name in before
                if field_name in after and before[field_name] != after[field_name]
            ]

            html = []
            html.append("<div style='font-family: sans-serif;'>")
            html.append("<h3 style='color: #202124; margin-bottom: 20px;'>Product Revision Comparison</h3>")
            html.append("<div class='card mb-4 shadow-sm' style='border-radius: 8px;'>")
            html.append("<div class='card-header bg-light'><b>Product Field Changes</b></div>")
            html.append("<div class='card-body p-0'>")

            if not changes:
                html.append("<p class='p-3 text-muted mb-0'>No changes detected since ECO was started.</p>")
            else:
                html.append("<table class='table table-hover mb-0'>")
                html.append("<thead class='table-light'><tr><th>Field</th><th>Before</th><th>After</th></tr></thead>")
                html.append("<tbody>")
                for field_name, before_val, after_val in changes:
                    field = product._fields.get(field_name)
                    field_label = field.string if field else field_name
                    html.append(
                        f"<tr class='table-warning'>"
                        f"<td><b>{field_label}</b></td>"
                        f"<td style='color: #bd2130;'>{before_val or '-'}</td>"
                        f"<td style='color: #1e7e34; font-weight: bold;'>{after_val or '-'}</td>"
                        f"</tr>"
                    )
                html.append("</tbody></table>")

            html.append("</div></div></div>")
            return "".join(html)

        else:
            return "<div class='alert alert-info'>Revision comparison is only supported for BoM-based ECOs.</div>"

        return "".join(html)
