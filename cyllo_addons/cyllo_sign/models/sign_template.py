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
import base64
import io

from PyPDF2 import PdfFileReader

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SignTemplate(models.Model):
    """
        A template for signable documents (PDF files).
        Templates define the structure of the signing process, including
        fields, roles, and associated tags. Each template can be reused
        across multiple sign requests.
    """
    _name = 'sign.template'
    _description = "Sign Template"
    _inherit = ["mail.thread"]
    _order = 'priority desc, create_date desc'

    name = fields.Char()
    data = fields.Binary()
    item_ids = fields.One2many('sign.template.item', 'template_id')
    tags_ids = fields.Many2many('sign.tag')
    company_id = fields.Many2one('res.company', index=True,
                                 default=lambda self: self.env.company,
                                 help="Company related to the request")
    image_1920 = fields.Image(string='Preview Image',
                              help='Preview image of PDF')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Favorite'),
    ], default='0', string="Favorite")

    def unlink(self):
        # Check if the template is linked to any sign.request
        sign_request_model = self.env['sign.request']
        for template in self:
            linked_requests = sign_request_model.search(
                [('template_id', '=', template.id)])
            if linked_requests:
                raise ValidationError((
                                          "The template '%s' cannot be deleted because it is linked to one or more Sign Requests."
                                      ) % template.name)
        return super(SignTemplate, self).unlink()

    def action_configure(self):
        return {
            'type': 'ir.actions.client',
            'name': self.name,
            'tag': 'sign_configure',
            'params': {
                "res_model": 'sign.template',
                "res_id": self.id,
            }
        }

    def action_view_sign_generate(self):
        record = self.env['sign.generate'].create({
            'template_id': self.id
        })
        if record.is_active:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Generate Sign',
                'res_model': 'sign.generate',
                'res_id': record.id,
                'view_mode': 'form',
                'views': [[False, 'form']],
                'target': 'new',
            }
        else:
            raise ValidationError(
                "There are no signers available to send the template.")

    @api.model
    def get_pdf_page_count(self, res_id):
        """
        Get the total number of pages in the PDF associated with the given template.
        :param res_id: The ID of the `sign.template` record.
        :return: The total number of pages in the PDF.
        """
        template = self.browse(res_id)
        if not template or not template.data:
            raise ValidationError(
                "No PDF file is associated with this template.")

        # Decode the binary PDF data
        pdf_data = io.BytesIO(base64.b64decode(template.data))
        try:
            pdf_reader = PdfFileReader(pdf_data)
            return len(pdf_reader.pages)
        except Exception as e:
            raise ValidationError(f"Failed to read PDF: {e}")

    @api.model
    def get_datas(self, resId, request_id=False):
        """
        Get template data with optional request-specific items
        :param resId: Template ID
        :param request_id: Optional sign.request ID for getting request-specific data
        """
        template = self.browse(resId)
        if request_id:
            request = self.env['sign.request'].browse(request_id)
            request_items = self.env['sign.request.item'].search([
                ('request_id', '=', request_id),
                ('template_item_id', 'in', template.item_ids.ids)
            ])

            if not request_items:
                request_items = self._create_request_items(template, request)

            template_items = [{
                'id': item.template_item_id.id,
                'field_id': item.template_item_id.field_id.id,
                'name': item.name,
                'role_id': item.role_id.id,
                'page': item.page,
                'required': item.required,
                'position_x': item.position_x,
                'position_y': item.position_y,
                'position_x_px': item.position_x_px,
                'position_y_px': item.position_y_px,
                'width': item.width,
                'height': item.height,
                'placeholder': item.placeholder,
                'color': item.color,
                'field_type': item.field_type,
                'signature': item.signature,
                'request_item_id': item.id,
                'value': item.value,
            } for item in request_items]
        else:
            template_items = template.item_ids.read()

        return {
            "template": template.read(),
            "template_items": template_items,
            "roles": self.env["sign.role"].search_read([]),
            "fields": self.env["sign.field"].search_read([])
        }

    def _create_request_items(self, template, request):
        """Create request-specific items from template items"""
        RequestItem = self.env['sign.request.item']
        request_items = []

        for template_item in template.item_ids:
            request_items.append(RequestItem.create({
                'request_id': request.id,
                'template_item_id': template_item.id,
                'role_id': template_item.role_id.id,
                'required': template_item.required,
                'signature': False,
                'name': template_item.name,
                'page': template_item.page,
                'position_x': template_item.position_x,
                'position_y': template_item.position_y,
                'position_x_px': template_item.position_x_px,
                'position_y_px': template_item.position_y_px,
                'width': template_item.width,
                'height': template_item.height,
                'placeholder': template_item.placeholder,
                'color': template_item.color,
                'field_type': template_item.field_type
            }))

        return request_items

    def view_record(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def delete_record(self):
        self.unlink()

    def add_item(self, field=None, required=False, page=None,
                 position_x=None, position_y=None,
                 placeholder=None, position_x_px=None, position_y_px=None):
        role_id = self.env['sign.role'].search([], limit=1)
        field_id = self.env['sign.field'].browse(field)
        vals = {
            'template_id': self.id,
            'name': field_id.name,
            'field_id': field_id.id,
            'role_id': role_id.id,
            'required': required,
            'page': page,
            'position_x': position_x,
            'position_y': position_y,
            'width': field_id.default_width,
            'height': field_id.default_height,
            'placeholder': placeholder,
            'color': role_id.color,
            'position_x_px': position_x_px,
            'position_y_px': position_y_px
        }
        return self.env['sign.template.item'].create(vals).id


class SignTemplateItem(models.Model):
    """
        A field inside a sign template that defines what signers need to fill in.
        For example: text, date, or signature fields.
        Each item belongs to a role and specifies its position on a PDF page.
    """
    _name = 'sign.template.item'
    _description = 'Sign Template Item'

    name = fields.Char()
    template_id = fields.Many2one('sign.template')
    field_id = fields.Many2one('sign.field')
    role_id = fields.Many2one('sign.role')
    required = fields.Boolean()
    page = fields.Integer()
    position_x = fields.Float()
    position_y = fields.Float()
    position_x_px = fields.Float()
    position_y_px = fields.Float()
    width = fields.Float()
    height = fields.Float()
    placeholder = fields.Char(readonly=False, store=True)
    color = fields.Integer(related='role_id.color')
    signature = fields.Html()
    field_type = fields.Selection(related='field_id.field_type')
    value = fields.Char(help="Stored value for text fields")

    def get_datas(self):
        """Get information about the template item."""
        self.ensure_one()
        return {
            "id": self.id,
            "field_id": self.field_id.id,
            "name": self.field_id.name,
            "role_id": self.role_id.id,
            "page": self.page,
            "required": self.required,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "width": self.width,
            "height": self.height,
            "placeholder": self.placeholder,
            "color": self.color,
            "field_type": self.field_id.field_type,
            "value": self.value,
        }
