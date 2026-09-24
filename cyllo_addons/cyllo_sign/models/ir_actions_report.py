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
import base64
import io
import re
import logging

_logger = logging.getLogger(__name__)

try:
    import pdfplumber
except ImportError:
    _logger.warning("pdfplumber not found, signature anchor detection will be disabled.")
    pdfplumber = None

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def action_send_for_signature(self, doc_ids):
        """
        Universal entry point for the signature workflow.
        1. Renders the report PDF.
        2. Detects [[SIGN:role]] anchors.
        3. Creates a sign.template and sign.request.
        """
        self.ensure_one()
        if not pdfplumber:
            raise UserError(_("The 'pdfplumber' library is required for signature detection."))

        if not doc_ids:
            return False

        # Generate the PDF
        # We use sudo to ensure we can render the report regardless of ACLs on the report itself
        pdf_content, _unused = self.sudo()._render_qweb_pdf(self.id, [doc_ids[0]])
        
        # Detect anchors
        anchors = self._detect_signature_anchors(pdf_content)
        if not anchors:
            raise UserError(_("No signature anchors found in the generated document. "
                              "Please ensure you've added Signature elements in the report editor."))

        # Create a temporary sign.template for this specific request
        # In a production system, we might want to cache these or link to the ir.actions.report
        template = self.env['sign.template'].sudo().create({
            'name': f"Template for {self.name}",
            'data': base64.b64encode(pdf_content),
        })

        # Find the source record to extract partners for roles
        source_record = self.env[self.model].browse(doc_ids[0])
        
        # Create template items (fields) based on detected anchors
        # Mapping roles to partners (basic heuristic)
        role_partner_map = self._map_roles_to_partners(source_record, anchors)
        
        # We need to make sure we have the roles in the system
        Role = self.env['sign.role'].sudo()
        Field = self.env['sign.field'].sudo()
        sign_field = Field.search([('field_type', '=', 'signature')], limit=1)
        if not sign_field:
             # Fallback: create signature field if missing
             sign_field = Field.create({'name': 'Signature', 'field_type': 'signature'})

        for anchor in anchors:
            role_name = anchor['role']
            role = Role.search([('name', '=ilike', role_name)], limit=1)
            if not role:
                role = Role.create({'name': role_name.capitalize()})
            
            self.env['sign.template.item'].sudo().create({
                'template_id': template.id,
                'field_id': sign_field.id,
                'role_id': role.id,
                'name': 'Sign',
                'placeholder': 'Sign',
                'page': anchor['page'],
                'position_x': anchor['x'],
                'position_y': anchor['y'],
                'width': 20,  # 20% of page width
                'height': 4,  # 8% of page height
                'required': True,
            })

        # Create the sign.request (draft)
        sign_request = self.env['sign.request'].sudo().create({
            'name': f"Sign Request: {source_record.display_name}",
            'template_id': template.id,
            'data': template.data,
            'res_model': self.model,
            'res_id': source_record.id,
            'requester_ids': [
                (0, 0, {
                    'role_id': Role.search([('name', '=ilike', role_name)], limit=1).id,
                    'partner_id': partner_id,
                }) for role_name, partner_id in role_partner_map.items()
            ]
        })

        # Return a URL action to completely exit Studio and enter the Sign module
        # Landing on the specific Sign Request we just created
        menu = self.env.ref('cyllo_sign.menu_cyllo_sign_root', raise_if_not_found=False)
        action = self.env.ref('cyllo_sign.action_view_all_requests', raise_if_not_found=False)
        
        url = f'/web#id={sign_request.id}&model=sign.request&view_type=form'
        if action:
            url += f'&action={action.id}'
        if menu:
            url += f'&menu_id={menu.id}'

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    def _detect_signature_anchors(self, pdf_content):
        """Detect [[SIGN:role]] text anchors in the PDF."""
        anchors = []
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for i, page in enumerate(pdf.pages):
                # Search for the anchor pattern
                text_instances = page.extract_text_all() if hasattr(page, 'extract_text_all') else []
                # Fallback to standard extract_words if extract_text_all is not available
                words = page.extract_words()
                
                # Combine words to find our tokens
                # Since [[SIGN:role]] might be split across "words" by pdfplumber
                # we search in the full text and try to find positions
                page_text = page.extract_text() or ""
            
                _logger.debug("Extracted text from PDF page %s: %s", i + 1, page_text)
                # Use a very loose regex to handle fragmentation (noise like underscores between letters)
                # We search for the pattern [[ SIGN : role ]] allowing any non-bracket noise in between
                noisy_regex = re.compile(r'\[+[^\[\]]*S[^\[\]]*I[^\[\]]*G[^\[\]]*N[^\[\]]*:([^\[\]]+)\]+', re.IGNORECASE)
                matches = list(noisy_regex.finditer(page_text))
                
                for match in matches:
                    # Clean the captured role name (remove noise like underscores)
                    raw_role = match.group(1)
                    role = re.sub(r'[^a-zA-Z0-9]', '', raw_role).lower()
                    if not role:
                        continue

                    # Find the word that corresponds to this match
                    # Since fragmentation is high, we look for words that contain 'SIGN' and the role
                    found_word = None
                    for w in words:
                        clean_word = re.sub(r'[^a-zA-Z0-9]', '', w['text']).lower()
                        if "sign" in clean_word and role in clean_word:
                            found_word = w
                            break
                    
                    if found_word:
                        # Convert to percentages (0-100)
                        # pdfplumber coordinates are top-left based (x0, top, x1, bottom)
                        # We use the center of the word for the anchor point
                        x_center = (found_word['x0'] + found_word['x1']) / 2
                        y_center = (found_word['top'] + found_word['bottom']) / 2
                        
                        anchors.append({
                            'role': role,
                            'page': i + 1,
                            'x': (x_center / page.width) * 100,
                            'y': (y_center / page.height) * 100,
                        })
        return anchors

    def _map_roles_to_partners(self, record, anchors):
        """Map roles found in anchors to partners on the record."""
        mapping = {}
        unique_roles = set(a['role'] for a in anchors)
        
        for role in unique_roles:
            partner = False
            # Heuristic 1: If role name matches a field name on the record
            if role in record._fields and record._fields[role].type == 'many2one' and record._fields[role].comodel_name == 'res.partner':
                partner = record[role]
            # Heuristic 2: Common field mappings
            elif role == 'customer' and 'partner_id' in record._fields:
                partner = record.partner_id
            elif role == 'vendor' and 'partner_id' in record._fields:
                partner = record.partner_id
            elif role == 'internal' and 'user_id' in record._fields:
                partner = record.user_id.partner_id
            
            if partner:
                _logger.info("Mapped role '%s' to partner '%s' (%s)", role, partner.name, partner.id)
                mapping[role] = partner.id
            else:
                _logger.warning("Could not map role '%s' to a partner on record %s", role, record.display_name)
                # Fallback to current user if no partner found? Or leave empty for manual selection?
                # For now, let's leave it empty to force the user to pick in the sign request wizard
                # if we were to show one, but here we go straight to action_sign.
                # Actually, sign_request.action_sign() expects signers.
                pass
                
        return mapping
