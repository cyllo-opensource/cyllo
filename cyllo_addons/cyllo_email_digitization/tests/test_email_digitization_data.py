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
import ast
import email
import json
import logging
import re

# imports of odoo
from odoo.addons.iap.tools import iap_tools
from odoo import _, fields, models
from odoo import release

DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'

# Import of unknown third party lib
_logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError as e:
    package_name = str(e).split(' ')[-1]
    _logger.debug('Cannot import the required external dependency: %s',
                  package_name)
    BeautifulSoup = None


class EmailDigitizationData(models.Model):
    """ Model representing data retrieved from emails."""
    _name = 'email.digitization.data'
    _inherit = ['portal.mixin', 'product.catalog.mixin', 'mail.thread',
                'mail.activity.mixin']
    _description = 'Email Data Retrieving'

    name = fields.Char(required=True)
    data = fields.Text(
        readonly=True,
        help="Details from the Email")
    html = fields.Html()
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments')
    email_digitization_config_id = fields.Many2one(
        'email.digitization.config',
        'Configuration',
        search=True)
    model_id = fields.Many2one(
        'ir.model',
        'Choose Model',
        domain="([('model', 'in', ('purchase.order', 'sale.order'))])")
    order_id = fields.Integer(string="Order ID")
    state = fields.Selection(
        [('draft', 'New'), ('done', 'Success'), ('error', 'Failed')],
        default='draft')
    digitize_message = fields.Char(string="Digitize Status", readonly=True)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company)
    model_name = fields.Char(related='model_id.model',store=True)

    def action_fetch(self):
        """
        Action method to fetch email details and populate fields accordingly."""
        subject = self.message_ids[0].subject
        from_name, from_address, = email.utils.parseaddr(
            self.message_ids[0].email_from)
        partner = self.env['res.partner'].search([('email', '=', from_address)])
        if partner:
            partner_name = partner[0].name
        else:
            partner_name = from_name
        body = self.message_ids[0].body
        soup = BeautifulSoup(body, 'html.parser')

        plain_text = soup.prettify()
        email_details = f"Subject: {subject} \n\n From: {partner_name}"
        self.data = email_details
        self.html = plain_text
        self.attachment_ids = self.message_ids[0].attachment_ids
        order_details = {}
        order_details.update(
            {'partner': partner, 'from_name': from_name, 'email': from_address})
        for tag in soup.find_all(True):
            tag.attrs = {}
        # Get the modified HTML code
        modified_html = soup
        for tag in modified_html.find_all():
            if not tag.get_text(strip=True):
                tag.decompose()
        if self.email_digitization_config_id.model_name == 'sale.order':
            prompt = (
                f"Find and extract product details, including product name, "
                f"product code, quantity, product unit of measure, from the"
                f" given HTML data.. Each product's details should be "
                f"represented as a dictionary. Create a list to store these"
                f" dictionaries. The dictionary keys should correspond to "
                f"'product_name', 'product_code', 'product_qty', 'product_uom'"
                f" .The response should only contain the list of dictionaries"
                f" no other text(it must very very strictly follow) "
                f"Use the provided HTML data: {modified_html}")
        else:
            if self.email_digitization_config_id.tax_type == 'tax_per_line':
                prompt = (
                    f"Find and extract product details,including product name, "
                    f"product code, quantity,product unit of measure, "
                    f"unit price, taxes,discount and subtotal, from the given"
                    f" HTML data.Each product's details should be represented"
                    f" as a dictionary. Create a list to store these "
                    f"dictionaries. The dictionary keys should correspond to"
                    f" 'product_name', 'product_code', 'product_qty', "
                    f"'price_unit',product_uom 'taxes_id','discount' and "
                    f"'price_subtotal',the taxes_id values are percentage(%)"
                    f" values don't take other values if it's null assign "
                    f"null,The Response must only contain the list no other "
                    f"text(it must very very strictly follow)."
                    f"Here's the HTML data: {modified_html} ")
            else:
                prompt = (
                    f"Find and extract product details,including product name,"
                    f" product code, quantity, product unit of measure,"
                    f" unit price, taxes, discount, and subtotal, from the"
                    f" given HTML data. Each product's details should be "
                    f"represented as a dictionary. Create a list to store these"
                    f" dictionaries. The dictionary keys should correspond to"
                    f" 'product_name','product_code', 'product_qty', "
                    f"'price_unit', 'product_uom', 'taxes_id', 'discount' and"
                    f" 'price_subtotal',the taxes_id values are percentage(%)"
                    f" values don't take other values.If taxes are null if "
                    f"it's null assign null, find a overall tax value with a"
                    f" percentage(%) and assign it to the 'taxes' key for every"
                    f" product. The response should only contain the list of "
                    f"dictionaries no other text(it must very very strictly"
                    f" follow). Use the provided HTML data: {modified_html}")
        conversation_history = [{'role': 'system',
                                 'content': 'You are a helpful assistant, your '
                                            'goal is extract details '
                                            'from this email data.'},
                                {'role': 'assistant',
                                 'content': 'What do you need ?'},
                                {'role': 'user', 'content': prompt}]
        if self.email_digitization_config_id.digitize_type == 'use_ai':
            order_lines = self.get_prod_details_ai(prompt, conversation_history)
        else:
            order_lines = self.get_prod_details_keyword(modified_html)
        order_details.update(
            {'order_lines': order_lines}) if order_lines else None
        return order_details

    def get_prod_details_ai(self, prompt, conversation_history):
        """Method to retrieve product details using an AI service."""
        try:
            config_parameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = config_parameter.get_param(
                'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
            response = iap_tools.iap_jsonrpc(
                olg_api_endpoint + "/api/olg/1/chat", params={
                    'prompt': prompt,
                    'conversation_history': conversation_history or [],
                    'version': release.version}, timeout=30)
            if response['status'] == 'success':
                return response['content']
            elif response['status'] == 'error_prompt_too_long':
                self.state = 'error'
                self.write(
                    {'digitize_message': _(f"Sorry, your content is too long")})
            else:
                self.state = 'error'
                self.write(
                    {'digitize_message': _(
                        f"Sorry, we could not generate a response. "
                        f"Please try again later.")})
        except Exception as exc:
            self.state = 'error'
            self.write({'digitize_message': _(
                f"Oops, it looks like our AI is unreachable!")})
            logging.error(f"AccessError details: {exc}")


    def get_prod_details_keyword(self, modified_html):
        """
        Extract product details from emails.
        Supports Table format, Keyword format, and Plain text format.
        Returns a list of dictionaries.
        """
        order_line_details = []

        if not modified_html:
            return order_line_details

        # ---------- 1) TABLE FORMAT ----------
        if self.model_id.model == 'sale.order':
            sale_line_conf = getattr(self.email_digitization_config_id, 'sale_line_field_details_ids', [])
        else:
            sale_line_conf = getattr(self.email_digitization_config_id, 'purchase_line_field_details_ids', [])
        for conf in sale_line_conf:
            line_keywords = conf.mapped('line_field_keyword_ids.name') or []
            if not line_keywords:
                continue

            try:
                tr_head_list = []
                for key in line_keywords:
                    trs = modified_html.select(f'tr:-soup-contains("{key}")')
                    if trs:
                        tr_head_list.extend(trs)

                found_head = next((tr for tr in tr_head_list if tr), None)
                if not found_head:
                    continue

                child_tags = found_head.find_all(['td', 'th'])
                tag_position = [i for i, tag in enumerate(child_tags) for key in line_keywords if key in tag.get_text()]
                desired_tr_tags = found_head.find_all_next('tr', recursive=False)

                for tr_tag_index, tr_tag in enumerate(desired_tr_tags):
                    tr_child_tags = tr_tag.find_all('td')
                    order_line = {'product_name': '', 'product_code': '', 'product_qty': '', 'product_uom': '',
                                  'price': ''}

                    for pos in tag_position:
                        if pos >= len(tr_child_tags):
                            continue
                        val = " ".join(tr_child_tags[pos].get_text(strip=True).split())
                        if self.model_id.model == 'sale.order':

                            if conf.sale_line_field_id.name == 'product_id':
                                order_line['product_name'] = val
                                match = re.search(r'\[([A-Z0-9_\-]+)\]|([A-Z0-9]{2,})', val)
                                order_line['product_code'] = match.group(1) if match and match.group(1) else (
                                    match.group(2) if match else '')
                            elif conf.sale_line_field_id.name == 'product_uom_qty':
                                qty = re.findall(r'\d+\.?\d*', val.replace(',', ''))
                                order_line['product_qty'] = qty[0] if qty else ''
                                uom = [word for word in val.split() if word.isalpha()]
                                order_line['product_uom'] = uom[0] if uom else ''
                            elif conf.sale_line_field_id.name == 'price_unit':
                                price_numbers = re.findall(r'\d+\.?\d*', val.replace(',', ''))
                                order_line['price'] = price_numbers[0] if price_numbers else ''
                        else:
                            if  conf.purchase_line_field_id.name == 'product_id':
                                order_line['product_name'] = val
                                match = re.search(r'\[([A-Z0-9_\-]+)\]|([A-Z0-9]{2,})', val)
                                order_line['product_code'] = match.group(1) if match and match.group(1) else (
                                    match.group(2) if match else '')
                            elif conf.purchase_line_field_id.name == 'product_qty':
                                qty = re.findall(r'\d+\.?\d*', val.replace(',', ''))
                                order_line['product_qty'] = qty[0] if qty else ''
                                uom = [word for word in val.split() if word.isalpha()]
                                order_line['product_uom'] = uom[0] if uom else ''
                            elif conf.purchase_line_field_id.name == 'price_unit':
                                price_numbers = re.findall(r'\d+\.?\d*', val.replace(',', ''))
                                order_line['price'] = price_numbers[0] if price_numbers else ''

                    if tr_tag_index < len(order_line_details):
                        order_line_details[tr_tag_index].update({k: v for k, v in order_line.items() if v})
                    elif any(order_line.values()):
                        order_line_details.append(order_line)

            except Exception as e:
                _logger.error(f"Error parsing table format: {e}")

        # ---------- 2) KEYWORD FORMAT ----------
        if not order_line_details:
            try:
                text_content = modified_html.get_text(separator=" ", strip=True)
                product_matches = re.findall(r'(?:Product|Item)[:\s]+([\w\s\[\]\-]+)', text_content, re.I)
                qty_matches = re.findall(r'(?:Qty|Quantity)[:\s]+([\d\.]+)', text_content, re.I)
                price_matches = re.findall(r'(?:Price|Unit\s*Price)[:\s]+([\d.,]+)', text_content, re.I)

                for i, product_name in enumerate(product_matches):
                    order_line = {
                        'product_name': product_name.strip(),
                        'product_code': '',
                        'product_qty': qty_matches[i] if i < len(qty_matches) else '1',
                        'product_uom': '',
                        'price': price_matches[i].replace(',', '') if i < len(price_matches) else '0.0'
                    }
                    order_line_details.append(order_line)
            except Exception as e:
                _logger.error(f"Error parsing keyword format: {e}")

        # ---------- 3) PLAIN TEXT / MIXED FORMAT ----------
        if not order_line_details:
            try:
                text_content = modified_html.get_text(separator=" ", strip=True)
                matches = re.findall(r'([A-Za-z]+)\s+([\d\.]+)\s+([\d\.]+)', text_content)
                for match in matches:
                    product, qty, price = match
                    order_line_details.append({
                        'product_name': product,
                        'product_code': '',
                        'product_qty': qty,
                        'product_uom': '',
                        'price': price
                    })
            except Exception as e:
                _logger.error(f"Error parsing plain text format: {e}")

        return order_line_details

    def action_digitize(self):
        """
        Method to digitize the email content and create or update corresponding
         records."""
        fetch = self.action_fetch()
        if self.model_id:
            orders = self.env[self.model_id.model].search([])
            order = [order for order in orders if order.name == self.name]
            if order:
                record = order[0]
            else:
                if fetch['partner']:
                    partner_id = fetch['partner']
                else:
                    partner_id = self.env['res.partner'].create(
                        {'name': fetch['from_name'], 'email': fetch['email']})
                record = self.env[self.model_id.model].create(
                    {'partner_id': partner_id.id,
                     'ocr_created': True})
                self.order_id = record.id
                self.message_ids[0].copy(
                    {'model': self.model_id.model, 'res_id': record.id})
            data = fetch[
                'order_lines'] if 'order_lines' in fetch.keys() else None
            self.action_create_order_lines(record, data) if data else ''
            return record
        else:
            self.write(
                {'digitize_message': _(f"The model field has no value..")})
            self.state = 'error'

    def action_create_order_lines(self, record, data):
        """
        Create/update order lines for a record.
        Works for sale.order and purchase.order.
        """
        created_any = False
        order_lines = []
        if isinstance(data, str):
            try:
                order_lines = json.loads(data.replace("'", '"'))
            except Exception:
                try:
                    order_lines = ast.literal_eval(data)
                except Exception:
                    m = re.search(r'\[.*\]', data, re.S)
                    if m:
                        try:
                            order_lines = json.loads(m.group())
                        except Exception:
                            order_lines = []
        else:
            order_lines = data or []

        if not order_lines:
            self.state = 'error'
            self.write({'digitize_message': 'Products not found'})
            return record

        for idx, line in enumerate(order_lines):
            try:
                # --- Raw values ---
                product_name = str(line.get('product_name', '')).strip()
                product_code = str(line.get('product_code', '')).strip()
                qty_raw = line.get('product_qty', line.get('product_uom_qty', 1))
                uom_name = str(line.get('product_uom', '')).strip()
                price_raw = line.get('price', line.get('price_unit', 0))
                discount_raw = line.get('discount', 0) or 0

                # --- Clean product name ---
                clean_name = re.sub(r'\[.*?\]', '', product_name).strip()
                if product_code and product_code in clean_name:
                    clean_name = clean_name.replace(product_code, '').strip()

                # --- Find product ---
                product_obj = None
                if product_code:
                    product_obj = self.env['product.product'].search([('default_code', '=', product_code)], limit=1)
                if not product_obj and clean_name:
                    product_obj = self.env['product.product'].search([('name', 'ilike', clean_name)], limit=1)
                if not product_obj and clean_name:
                    product_obj = self.env['product.product'].search([('display_name', 'ilike', clean_name)], limit=1)

                # --- Prepare vals ---
                vals = {'order_id': record.id}
                if product_obj:
                    vals['product_id'] = product_obj.id
                else:
                    if self.model_id.model != 'purchase.order':
                        self.state = 'error'
                        self.write({'digitize_message': f'Product not found: {product_name}'})
                        record.unlink()
                        self.order_id = None
                        return record
                    else:
                        vals['name'] = clean_name or "Unknown Product"

                # --- Quantity ---
                qty_list = re.findall(r'\d+\.?\d*', str(qty_raw))
                qty_val = float(qty_list[0]) if qty_list else 1.0
                if self.model_id.model == 'purchase.order':
                    vals['product_qty'] = qty_val
                else:
                    vals['product_uom_qty'] = qty_val

                # --- UoM ---
                if uom_name:
                    uom_obj = self.env['uom.uom'].search([('name', 'ilike', uom_name)], limit=1)
                    if uom_obj:
                        vals['product_uom'] = uom_obj.id

                # --- Price & Discount ---
                price_list = re.findall(r'\d+\.?\d*', str(price_raw))
                vals['price_unit'] = float(price_list[0]) if price_list else 0.0

                try:
                    discount_list = re.findall(r'\d+\.?\d*', str(discount_raw))
                    vals['discount'] = float(discount_list[0]) if discount_list else 0.0
                except Exception:
                    vals['discount'] = 0.0

                # --- Create order line ---
                record.order_line.create(vals)
                created_any = True

            except Exception as e:
                _logger.exception(f"Error creating order line: {line}")
                continue

        # --- Finalize ---
        if created_any:
            self.state = 'done'
            self.write({'digitize_message': 'Products successfully added'})
        else:
            self.state = 'error'
            self.write({'digitize_message': 'No valid products were added'})

        return record

    def action_create_product(self, product_name, extracted_price_unit,
                              product_code, product_uom, record):
        """Method to create a product based on extracted details."""
        if (self.email_digitization_config_id.product_creation_type ==
                'create_product'):
            name_without_code = [product_name.replace(name, '') for name in
                                 product_name.split() if
                                 product_code and product_code in product_name]
            product_name = name_without_code[
                0] if name_without_code else product_name
            ocr_product = self.env['product.product'].create(
                {'name': product_name, 'default_code': product_code,
                 'standard_price': extracted_price_unit, 'ocr_product': True,
                 'detailed_type': 'product'})
            self.env['product.supplierinfo'].create(
                {'partner_id': record.partner_id.id,
                 'product_id': ocr_product.id,
                 'product_name': product_name, 'product_code': product_code,
                 'price': extracted_price_unit})
            uom_list = self.env['uom.uom'].search([])
            found_uom = [uom for uom in uom_list if
                         uom.name == product_uom] if product_uom else []
            if found_uom:
                ocr_product.write({'uom_id': found_uom[0].id})
            return ocr_product

    def action_view_order(self):
        """Method to view the associated order."""
        return {
            'name': _('Order'),
            'view_mode': 'form',
            'res_model': self.model_id.model,
            'res_id': self.order_id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_retry_digitization(self):
        """Method to retry digitization."""
        if not self.order_id:
            self.action_digitize()
        return
