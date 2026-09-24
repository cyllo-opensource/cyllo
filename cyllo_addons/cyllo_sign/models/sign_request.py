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
import hashlib
import urllib
from base64 import b64decode, b64encode
from datetime import datetime
from io import BytesIO

from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SignRequest(models.Model):
    """
        Represents a document signing request.
        Tracks template, state, signers, validity, and related actions.
    """
    _name = 'sign.request'
    _description = 'Sign Request'

    name = fields.Char(required=True)
    user_id = fields.Many2one('res.users', string="Assigned By", default=lambda self: self.env.user)
    template_id = fields.Many2one('sign.template', ondelete='restrict')
    data = fields.Binary()
    validity = fields.Date()
    state = fields.Selection([('draft', 'Draft'), ('partial', 'Partially Signed'),
                              ('signed', 'Fully Signed'), ('cancel', 'Cancelled'),
                              ('expired', 'Expired')], default="draft")
    company_id = fields.Many2one('res.company', index=True, default=lambda self: self.env.company,
                                 help="Company related to the request")
    requester_ids = fields.One2many('sign.requester', 'request_id')
    allowed_user_ids = fields.Many2many('res.users', string='Allowed users',
                                        help="Users allowed to read record")
    value = fields.Char(help="Stored value for text fields")
    email_cc_ids = fields.Many2many('res.partner', string='Email CC')
    custom_subject = fields.Char(string='Custom Email Subject')
    custom_message = fields.Html(string='Custom Email Message')

    # Source document tracking
    res_model = fields.Char(string='Source Model', index=True)
    res_id = fields.Many2oneReference('Source ID', model_field='res_model', index=True)

    def action_sign(self):
        """Open the signing interface for the current user if authorized."""
        self.ensure_one()
        signer = self.requester_ids.filtered(lambda r: r.partner_id == self.env.user.partner_id)
        if signer:
            return {
                "type": "ir.actions.client",
                "tag": "sign_configure",
                "name": self.template_id.name,
                "params": {
                    "res_model": self.template_id._name,
                    "res_id": self.template_id.id,
                    "to_sign": True,
                    "request_id": self.id,
                    "requester_ids": signer.ids,
                    "role": signer.role_id.ids,
                    "roles": signer.read()
                },
            }
        else:
            raise ValidationError('Only authorized person can sign!')

    def action_cancel(self):
        """Mark the sign request as cancelled."""
        self.state = 'cancel'

    def action_print_signed_document(self):
        """Download the signed document as PDF if available."""
        self.ensure_one()
        if self.data:
            filename = f"{self.name}"
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self._name}/{self.id}/data/{filename}?download=true',
                'target': 'self',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'No data available to download.',
                    'sticky': False,
                }
            }

    @api.model
    def get_user(self, user_id):
        """Get the user details from userID"""
        return self.env['res.partner'].sudo().browse(user_id).read()

    def get_roles(self):
        """Get roles assigned to the current logged-in user for this request."""
        signer = self.requester_ids.filtered(lambda r: r.partner_id == self.env.user.partner_id)
        return signer.read()

    def get_sign_url(self, signer_id, role_id):
        """Generate signing URL for a specific signer."""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        params = {
            'res_model': 'sign.template',
            'res_id': self.template_id.id,
            'to_sign': True,
            'request_id': self.id,
            'requester_ids': self.requester_ids.mapped('id'),
            'role': role_id,
            'partner_id': signer_id,
            'portal': True,
            'mail': True,
        }

        sign_url = f"{base_url}/web/portal/sign"
        query_string = urllib.parse.urlencode(params)
        full_url = f"{sign_url}?{query_string}"

        return full_url

    def send_sign_request_email(self):
        """Send the sign request email using the configured template."""
        mail_template = self.env.ref('cyllo_sign.email_template_sign_request')
        for record in self:
            for signer in self.requester_ids:
                mail_template['email_to'] = signer.partner_id.email
                mail_template['email_cc'] = ','.join(record.email_cc_ids.mapped('email')) if record.email_cc_ids else False
                mail_template['subject'] = record.custom_subject if record.custom_subject else 'Sign Request: ' + record.display_name
                mail_template.with_context({
                    'signer_id': signer.partner_id.id,
                    'name': signer.partner_id.name,
                    'role': signer.role_id,
                    'custom_message': record.custom_message,
                }, record=record).sudo().send_mail(record.id, force_send=True)

    def _expire_request(self):
        """Expire requests that have passed their validity date."""
        today = fields.Date.today()
        requests = self.search([('state', 'not in', ['signed', 'cancel'])])
        for request in requests:
            if request.validity:
                if request.validity < today:
                    request.state = 'expired'


class SignRequesters(models.Model):
    """
        Represents an individual signer assigned to a sign request.
        Tracks partner, role, and signed status.
    """
    _name = 'sign.requester'
    _description = 'Sign Requesters'

    partner_id = fields.Many2one('res.partner')
    role_id = fields.Many2one('sign.role')
    signed_on = fields.Datetime()
    color = fields.Integer(related='role_id.color')
    request_id = fields.Many2one('sign.request')
    data = fields.Binary(related="request_id.data", help="Binary data of the sign request")

    def action_sign(self, items, access_token=False):
        """Action to sign and print the document."""
        input_data = BytesIO(b64decode(self.request_id.data))
        reader = PdfFileReader(input_data)
        output = PdfFileWriter()
        pages = {}
        # Create a copy of original pages
        for page_number in range(1, reader.numPages + 1):
            pages[page_number] = reader.getPage(page_number - 1)
        for item in items:
            signature_data = item["signature"]
            if signature_data:
                if signature_data.startswith('<p>') and signature_data.endswith('</p>'):
                    signature_data = signature_data.strip('<p>').strip('</p>')
                item['value'] = signature_data
            page_number = item.get('page')
            if item.get('value'):
                new_page = self._overwrite_pdf_page(item, pages[page_number].mediaBox)
                if new_page:
                    original_page = pages[page_number]
                    page = original_page.createBlankPage(width=new_page.mediaBox.getWidth(),
                                                         height=new_page.mediaBox.getHeight())
                    page.mergePage(original_page)
                    page.mergePage(new_page)
                    pages[page_number] = page
            for rec in self.request_id.requester_ids:
                if rec.role_id.id == item.get('role_id') and item.get('value') != False and not rec.signed_on:
                    rec.write({'signed_on': fields.Datetime.now()})
        for page_number in pages:
            output.addPage(pages[page_number])
        output_stream = BytesIO()
        output.write(output_stream)
        output_stream.seek(0)
        signed_pdf = output_stream.read()
        hashlib.sha1(signed_pdf).hexdigest()
        self.request_id.write({"data": b64encode(signed_pdf)})
        ir_values = {
            'name': self.request_id.name,
            'type': 'binary',
            'datas': self.request_id.data,
            'store_fname': self.request_id.data,
            'mimetype': 'application/pdf',
            'res_model': 'sign.request',
        }
        flag = True
        for signer in self.request_id.requester_ids:
            if not signer.signed_on:
                flag = False
        if flag:
            self.request_id.state = 'signed'
        else:
            self.request_id.state = 'partial'

    def _overwrite_pdf_page(self, item, box):
        """Get PDF page based on item field type."""
        return getattr(self, "_overwrite_pdf_page_%s" % item.get("field_type"))(item, box)

    def _overwrite_pdf_page_text(self, item, box):
        """Overwrite PDF page for text with pixel-based coordinates."""
        packet = BytesIO()
        # PDF dimensions in points (1 point = 1/72 inch)
        can = canvas.Canvas(packet, pagesize=(box.getWidth(), box.getHeight()))
        par = Paragraph(item.get('value'))
        # Get box dimensions
        box_width = float(box.getWidth())
        box_height = float(box.getHeight())
        # Get dimensions in percentage
        width_pct = item.get('width')  # e.g., 10 for 10%
        height_pct = item.get('height')  # e.g., 5 for 5%
        x_pct = item.get('position_x')  # e.g., 25 for 25%
        y_pct = item.get('position_y')  # e.g., 50 for 50%
        # Convert percentage to points
        width = (width_pct / 100.0) * box_width
        height = (height_pct / 100.0) * box_height
        x = (x_pct / 100.0) * box_width
        y = box_height - ((y_pct / 100.0) * box_height) - height
        par.wrap(width, height)
        par.drawOn(can, x, y)
        can.save()
        packet.seek(0)
        new_pdf = PdfFileReader(packet)
        return new_pdf.getPage(0)

    def _overwrite_pdf_page_date(self, item, box):
        """
        Overwrite PDF page for a date field with pixel-based coordinates.
        """
        packet = BytesIO()
        # PDF dimensions in points (1 point = 1/72 inch)
        can = canvas.Canvas(packet, pagesize=(box.getWidth(), box.getHeight()))
        # Extract and format the date value
        date_value = item.get('value')
        try:
            # Parse the date value
            date_obj = datetime.strptime(date_value, "%d-%m-%Y")
            formatted_date = date_obj.strftime("%d-%m-%Y")
        except (ValueError, TypeError):
            formatted_date = "Invalid Date"
        # Get box dimensions
        box_width = float(box.getWidth())
        box_height = float(box.getHeight())
        # Get dimensions in percentage
        width_pct = item.get('width')  # e.g., 10 for 10%
        height_pct = item.get('height')  # e.g., 5 for 5%
        x_pct = item.get('position_x')  # e.g., 25 for 25%
        y_pct = item.get('position_y')  # e.g., 50 for 50%
        # Convert percentage to points
        height = (height_pct / 100.0) * box_height
        x = (x_pct / 100.0) * box_width
        y = box_height - ((y_pct / 100.0) * box_height) - height
        # Set font and draw the formatted date on the canvas
        can.setFont("Helvetica", 12)  # Example font and size
        can.drawString(x, y, formatted_date)
        can.save()
        packet.seek(0)
        new_pdf = PdfFileReader(packet)
        return new_pdf.getPage(0)

    def _overwrite_pdf_page_signature(self, item, box):
        """Overwrite PDF page for signature with percentage-based coordinates."""
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=(box.getWidth(), box.getHeight()))
        if not item["value"]:
            return False
        # Get box dimensions
        box_width = float(box.getWidth())
        box_height = float(box.getHeight())
        # Get dimensions in percentage
        width_pct = item.get('width')  # e.g., 10 for 10%
        height_pct = item.get('height')  # e.g., 5 for 5%
        x_pct = item.get('position_x')  # e.g., 25 for 25%
        y_pct = item.get('position_y')  # e.g., 50 for 50%
        # Convert percentage to points
        width = (width_pct / 100.0) * box_width
        height = (height_pct / 100.0) * box_height
        x = (x_pct / 100.0) * box_width
        y = box_height - ((y_pct / 100.0) * box_height) - height
        par = Image(BytesIO(b64decode(item["value"])), width=width, height=height)
        par.drawOn(can, x, y)
        can.save()
        packet.seek(0)
        new_pdf = PdfFileReader(packet)
        return new_pdf.getPage(0)


class SignRequestItem(models.Model):
    """
        Represents a specific field (text, signature, date) that needs to be filled
        or signed within a request document.
    """
    _name = 'sign.request.item'
    _description = 'Sign Request Item'

    request_id = fields.Many2one('sign.request', required=True, ondelete='cascade')
    template_item_id = fields.Many2one('sign.template.item', required=True, ondelete='cascade')
    role_id = fields.Many2one('sign.role')
    required = fields.Boolean()
    signature = fields.Html()
    value = fields.Char(help="Stored value for text fields")
    position_x_px = fields.Float()
    position_y_px = fields.Float()
    # Store template values instead of relating them
    name = fields.Char()
    page = fields.Integer()
    position_x = fields.Float()
    position_y = fields.Float()
    width = fields.Float()
    height = fields.Float()
    placeholder = fields.Char()
    color = fields.Integer()
    field_type = fields.Selection([
        ('text', 'Text'),
        ('signature', 'Signature'),
        ('date', 'Date')
    ])

    _sql_constraints = [
        ('unique_template_item_request',
         'unique(template_item_id, request_id)',
         'Only one sign request item per template item per request!')
    ]
