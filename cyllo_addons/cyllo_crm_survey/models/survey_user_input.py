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
##############################################################################
from odoo import models


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    def _mark_done(self):
        """Create a lead from survey responses."""
        res = super()._mark_done()
        for user_input in self:
            if user_input.survey_id.create_lead and not user_input.test_entry:
                lead_vals = {
                    'type': 'opportunity',
                    'user_id': False,
                }
                if user_input.partner_id:
                    lead_vals['partner_id'] = user_input.partner_id.id
                m2m_values = {}
                explicit_lead_name = False
                contact_or_partner_name = False
                for line in user_input.user_input_line_ids:
                    if line.question_id.lead_field_id:
                        field_name = line.question_id.lead_field_id.name
                        field_type = line.question_id.lead_field_id.ttype
                        value = False
                        if line.answer_type == 'char_box':
                            value = line.value_char_box
                        elif line.answer_type == 'text_box':
                            value = line.value_text_box
                        elif line.answer_type == 'numerical_box':
                            value = line.value_numerical_box
                        elif line.answer_type == 'date':
                            value = line.value_date
                        elif line.answer_type == 'datetime':
                            value = line.value_datetime
                        elif line.answer_type == 'suggestion':
                            value = line.suggested_answer_id.value
                        if value is not False and value is not None:
                            # Keep track of submitted names for setting Lead name
                            if field_name in ('name', 'display_name'):
                                explicit_lead_name = str(value)
                            elif field_name in ('contact_name', 'partner_name'):
                                contact_or_partner_name = str(value)
                            elif field_name == 'partner_id':
                                contact_or_partner_name = str(value)

                            if field_type == 'many2one':
                                relation = line.question_id.lead_field_id.relation
                                if relation:
                                    res_search = self.env[relation].name_search(value, operator='=', limit=1)
                                    if not res_search and field_name != 'partner_id':
                                        res_search = self.env[relation].name_search(value, operator='ilike', limit=1)
                                    val_id = res_search[0][0] if res_search else False
                                    if field_name == 'partner_id' and not val_id:
                                        new_partner = self.env['res.partner'].create({'name': str(value)})
                                        val_id = new_partner.id
                                        contact_or_partner_name = new_partner.name
                                    lead_vals[field_name] = val_id
                                    if field_name == 'partner_id' and val_id and not contact_or_partner_name:
                                        partner = self.env['res.partner'].browse(val_id)
                                        contact_or_partner_name = partner.name
                            elif field_type == 'many2many':
                                relation = line.question_id.lead_field_id.relation
                                if relation:
                                    res_search = self.env[relation].name_search(value, operator='=', limit=1)
                                    if not res_search:
                                        res_search = self.env[relation].name_search(value, operator='ilike', limit=1)
                                    if res_search:
                                        m2m_values.setdefault(field_name, []).append(res_search[0][0])
                            elif field_type == 'selection':
                                selection_options = self.env['crm.lead'].fields_get([field_name])[field_name].get('selection', [])
                                match_key = False
                                for key, label in selection_options:
                                    if str(key).strip().lower() == str(value).strip().lower() or \
                                       str(label).strip().lower() == str(value).strip().lower():
                                        match_key = key
                                        break
                                lead_vals[field_name] = match_key if match_key else value
                            elif field_type == 'integer':
                                try:
                                    lead_vals[field_name] = int(float(value))
                                except (ValueError, TypeError):
                                    pass
                            elif field_type in ('float', 'monetary'):
                                try:
                                    lead_vals[field_name] = float(value)
                                except (ValueError, TypeError):
                                    pass
                            else:
                                if field_name != 'display_name':
                                    lead_vals[field_name] = value

                for f_name, ids in m2m_values.items():
                    lead_vals[f_name] = [(6, 0, ids)]

                if explicit_lead_name:
                    lead_vals['name'] = explicit_lead_name
                elif contact_or_partner_name:
                    lead_vals['name'] = f"{contact_or_partner_name} - Opportunity"
                else:
                    lead_vals['name'] = f"{user_input.survey_id.title} - {user_input.partner_id.name if user_input.partner_id else 'Anonymous'}"

                if lead_vals:
                    lead = self.env['crm.lead'].create(lead_vals)
                    backend_url = f"/web#id={user_input.id}&model=survey.user_input&view_type=form"
                    frontend_url = f"/survey/print/{user_input.survey_id.access_token}?answer_token={user_input.access_token}"
                    message_body = f"<strong>Lead created from Survey:</strong> <a href='/web#id={user_input.survey_id.id}&model=survey.survey&view_type=form'>{user_input.survey_id.title}</a>.<br/>" \
                                   f"• <a href='{backend_url}' target='_blank'>View User Input in Backend</a><br/>" \
                                   f"• <a href='{frontend_url}' target='_blank'>View Print Answers (Frontend)</a>"
                    lead._message_log(body=message_body)
        return res
