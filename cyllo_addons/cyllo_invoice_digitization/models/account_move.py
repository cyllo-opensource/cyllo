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
import logging
import locale
import os
import re
import tempfile

from openai import AuthenticationError, OpenAI

# imports of odoo
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import AccessError
from odoo import _, Command, fields, models, release
from datetime import datetime

# Import of unknown third party lib
_logger = logging.getLogger(__name__)

GPT_MODEL = "gpt-3.5-turbo"
DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'

try:
    import camelot
    import fitz
    import pdfplumber
    import pandas as pd
except ImportError as e:
    package_name = str(e).split(' ')[-1]
    _logger.debug('Cannot import the required external dependency: %s',
                  package_name)


class AccountMove(models.Model):
    """
    Extends 'account.move' for OCR digitization to add required fields
    and methods."""
    _inherit = 'account.move'
    ocr_digitize_enabled = fields.Boolean(
        string="OCR Enabled",
        compute='_compute_ocr_digitize_enabled')
    ocr_digitize_completed = fields.Boolean(string="OCR success status")
    ocr_digitize_failed = fields.Boolean(string="OCR failed status")
    ocr_digitize_message = fields.Char(
        string="OCR Status",
        readonly=True)

    @property
    def invoice_digitization(self):
        """
        Retrieves the active invoice digitization record based on the current move type.
        """
        digitization_record = self.env['invoice.digitization'].search([
            ('active_configuration', '=', True),
            ('account_type', '=', self.move_type)
        ], limit=1)
        if not digitization_record:
            # Fallback to any active config when none matches this move_type
            # exactly (e.g. only a Customer Invoice config exists while a Vendor
            # Bill is digitized).
            digitization_record = self.env['invoice.digitization'].search([
                ('active_configuration', '=', True)
            ], limit=1)
        return digitization_record

    def _compute_ocr_digitize_enabled(self):
        """
        Compute the OCR digitization status for each record.
        The OCR digitization status is determined based on the configuration
        parameters and the automation type specified in the associated
        invoice digitization settings.
        """
        for rec in self:
            is_ocr_digitization = self.env[
                'ir.module.module'].sudo().search(
                [('name', '=', 'cyllo_invoice_digitization'),
                 ('state', '=', 'installed')])
            if is_ocr_digitization:
                # Retrieve the invoice digitization settings
                invoice_digitization = self.env['invoice.digitization'].search(
                    [('active_configuration', '=', True),
                     ('account_type', '=', rec.move_type)])
                if len(invoice_digitization) > 1:
                    raise ValidationError(
                        _("Only one invoice digitization method can be active at a time. Please deactivate the others before proceeding."))
                # Determine OCR digitization status based on automation type
                if invoice_digitization.automation_type == 'request_digitize':
                    rec.write({'ocr_digitize_enabled': True})
                else:
                    rec.write({'ocr_digitize_enabled': False})
            else:
                rec.write({'ocr_digitize_enabled': False})

    def process_auto_digitization(self):
        """Trigger automatic digitization on a freshly uploaded invoice/bill
        when an active configuration is set to ``auto_digitize``."""
        if self.move_type in ['out_invoice', 'in_invoice'] and self.env[
            'ir.module.module'].sudo().search_count([
            ('name', '=', 'cyllo_invoice_digitization'),
            ('state', '=', 'installed')
        ]):
            invoice_digitization = self.env['invoice.digitization'].search([
                ('active_configuration', '=', True),
                ('account_type', '=', self.move_type)
            ], limit=1)
            if not invoice_digitization:
                # Fallback to any active config so an upload still digitizes
                # even when no config matches this move_type exactly.
                invoice_digitization = self.env['invoice.digitization'].search([
                    ('active_configuration', '=', True)
                ], limit=1)
            if invoice_digitization and invoice_digitization.automation_type == 'auto_digitize' and \
                    self.state == 'draft' and self.message_main_attachment_id:
                try:
                    # Let action_send_digitization manage the status flags so a
                    # real failure is not masked as success.
                    self.action_send_digitization()
                except Exception as error:
                    self.ocr_digitize_failed = True
                    self.ocr_digitize_completed = False
                    _logger.exception("Auto digitization failed: %s", error)
                    self.write({
                        'ocr_digitize_message': _(
                            "Data cannot be read, digitization failed.")
                    })

    def action_send_digitization(self):
        """
        Perform OCR digitization on a PDF document attached to the record.
        This method reads the attached PDF document, extracts text content, and
        processes it to digitize relevant information, such as partner name,
        invoice fields, and invoice line details.
        :raises: Exception if an error occurs during digitization.
        """
        # Getting the file path from ir.attachments
        file_attachment = self.message_main_attachment_id
        # Check if the file is a PDF
        if not file_attachment or os.path.splitext(file_attachment.name)[
            1].lower() != '.pdf':
            # Handle non-PDF or missing attachments
            self.ocr_digitize_failed = True
            self.ocr_digitize_completed = False
            self.write({
                'ocr_digitize_message': 'Digitization now works only on PDF documents'
            })
            return
        file_path = file_attachment._full_path(file_attachment.store_fname)
        try:
            # Read the PDF using fitz (PyMuPDF)
            with fitz.open(file_path) as doc:
                text = "\n".join(

                    [page.get_text(flags=8).strip() for page in doc if
                     page.get_text(flags=8).strip()])

            # Read the PDF using pdfplumber (additional parsing for structure)
            with pdfplumber.open(file_path) as pdf:
                pdf_text = "\n".join(
                    [page.extract_text() for page in pdf.pages if
                     page.extract_text()])
                # Build text_list from the plain text (one entry per line)
                text_list = [[line] for line in pdf_text.splitlines() if line.strip()]

            # Read pdf into list of DataFrame
            # Extract invoice digitization settings
            invoice_digitization = self.env['invoice.digitization'].search(
                [('active_configuration', '=', True),
                 ('account_type', '=', self.move_type)], limit=1
            )
            if not invoice_digitization:
                # Fallback to any active config (e.g. only a Customer Invoice
                # config exists while a Vendor Bill is being digitized).
                invoice_digitization = self.env['invoice.digitization'].search(
                    [('active_configuration', '=', True)], limit=1)
            if not invoice_digitization:
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write(
                    {'ocr_digitize_message': _("Configure the Digitization.")})
                return
            # Handle manual digitization
            if invoice_digitization.automation_method == 'manual_digitization':
                self._process_digitization_manually(file_path, text)
            else:
                # AI-based digitization
                self._process_pdf_using_ai(pdf_text)

        except Exception as e:
            # Handle exceptions
            self.ocr_digitize_failed = True
            self.ocr_digitize_completed = False
            _logger.error(f"Error during digitization: {e}")
            self.write({
                'ocr_digitize_message': "Data cannot be read, digitization failed."
            })

    def _process_digitization_manually(self, file_path, text):
        """Manual digitization.

        Header fields (partner, dates, references) are read first from the PDF
        text. Product lines are then parsed directly from the text table, which
        is reliable for digital PDFs and independent of the optional ``camelot``
        binary dependency. When the text table cannot be parsed, it falls back
        to the keyword/column table extraction.
        """
        try:
            # 1. Header fields (text based, independent of the line table)
            self.find_partner(text)
            self.action_find_field_values(text)

            # 2. Product lines: parse the PDF text table directly
            parsed_lines = self._extract_lines_from_pdf_text(file_path)
            if parsed_lines:
                self._create_invoice_lines_from_parsed(parsed_lines)
            else:
                # Fallback: keyword/column table extraction
                self._extract_lines_from_table(file_path, text)

            # 3. Status: success when anything was captured
            if (self.invoice_line_ids or self.partner_id
                    or self.invoice_date or self.ref):
                self.ocr_digitize_completed = True
                self.ocr_digitize_failed = False
                if not self.invoice_line_ids:
                    self.write({'ocr_digitize_message': _(
                        "Header fields digitized. No invoice lines could be "
                        "detected from the document.")})
            else:
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    "Data cannot be read, digitization failed.")})
        except Exception as error:
            _logger.exception("Manual digitization failed: %s", error)
            self.ocr_digitize_failed = True
            self.ocr_digitize_completed = False
            self.write({'ocr_digitize_message': _(
                "Data cannot be read, digitization failed.")})

    def _extract_lines_from_table(self, file_path, text):
        """Fallback line extraction using camelot (lattice/stream) with a
        pdfplumber/word-clustering fallback, then the configured line keywords.
        Used only when the direct text-table parser finds no product lines."""
        combined_table = pd.DataFrame()
        table_data = []
        try:
            with open(file_path, mode='rb') as pdf_file:
                pdf_data = pdf_file.read()
        except OSError as error:
            _logger.warning("Could not read PDF for table extraction: %s", error)
            return
        with tempfile.NamedTemporaryFile(suffix='.pdf',
                                         delete=False) as temp_pdf_file:
            temp_pdf_file.write(pdf_data)
        tmp = temp_pdf_file.name
        tables_dfs = []
        try:
            tables = camelot.read_pdf(tmp, pages='all', flavor='lattice')
            if not tables:
                tables = camelot.read_pdf(tmp, flavor='stream', pages='all')
            if tables:
                combined_table = pd.concat(
                    [t.df for t in tables], ignore_index=True) \
                    if len(tables) > 1 else tables[0].df
                for table in tables:
                    table_data.append([
                        [item.replace('\xa0', ' ').strip()
                         for item in row if item.strip()]
                        for row in table.df.itertuples(index=False)])
        except Exception as error:
            _logger.warning("camelot extraction failed: %s", error)
        if not table_data:
            try:
                with pdfplumber.open(tmp) as pdf_doc:
                    for page in pdf_doc.pages:
                        tbls = page.extract_tables() or page.extract_tables(
                            table_settings={'vertical_strategy': 'text',
                                            'horizontal_strategy': 'text'})
                        for tbl in (tbls or []):
                            tables_dfs.append(
                                pd.DataFrame(tbl).fillna('').astype(str))
                if len(tables_dfs) > 1:
                    combined_table = pd.concat(tables_dfs, ignore_index=True)
                elif len(tables_dfs) == 1:
                    combined_table = tables_dfs[0]
                for frame in tables_dfs:
                    table_data.append([
                        [str(item).replace('\xa0', ' ').strip()
                         for item in row if str(item).strip()]
                        for row in frame.itertuples(index=False)])
            except Exception as error:
                _logger.warning("pdfplumber extraction failed: %s", error)
        if hasattr(combined_table, 'empty') and not combined_table.empty:
            column_values = self.action_get_invoice_line_columns(
                combined_table, text)
            self.action_create_products(combined_table, column_values)
            self.get_order_line(table_data, column_values)

    def _extract_lines_from_pdf_text(self, file_path):
        """Parse product lines directly from the invoice's text table.

        Locates the column header row (Description/Quantity/Unit Price/...),
        then parses each following product row from the RIGHT
        (amount, optional tax%, unit price, quantity) leaving the product name.
        Robust for clean digital PDFs and independent of camelot/ghostscript.
        """
        lines = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    lines.extend((page.extract_text() or '').split('\n'))
        except Exception as error:
            _logger.warning("Could not read PDF text lines: %s", error)
            return []
        header_index = None
        for index, line in enumerate(lines):
            low = line.lower()
            if (('description' in low or 'product' in low or 'item' in low)
                    and ('quantity' in low or 'qty' in low or 'price' in low)):
                header_index = index
                break
        if header_index is None:
            return []
        stop_words = ('untaxed amount', 'subtotal', 'sub total', 'total',
                      'tax ', 'amount due', 'balance', 'page ', 'thank you')
        # name | qty | unit_price | optional tax% | optional currency | amount
        row_re = re.compile(
            r'^(?P<name>.+?)\s+'
            r'(?P<qty>\d[\d,]*(?:\.\d+)?)\s+'
            r'(?:[a-zA-Z]+\s+)?'
            r'(?P<price>[\d,]+\.\d{2})(?:\s+|$)'
            r'(?:(?P<disc>\d+(?:\.\d+)?)(?:\s*%|)\s+)?'
            r'(?:(?P<tax>\d+(?:\.\d+)?)\s*%\s+)?'
            r'[^\d\-]*'
            r'(?P<amount>[\d,]+\.\d{2})\s*$'
        )
        parsed = []
        for line in lines[header_index + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if any(word in stripped.lower() for word in stop_words):
                break
            match = row_re.match(stripped)
            if match:
                parsed.append({
                    'name': match.group('name').strip(),
                    'quantity': float(match.group('qty').replace(',', '')),
                    'price_unit': float(match.group('price').replace(',', '')),
                    'tax': match.group('tax'),
                })
        return parsed

    def _create_invoice_lines_from_parsed(self, parsed_lines):
        """Create ``account.move.line`` records from parsed product line dicts,
        matching or creating each product and mapping the tax percentage."""
        tax_use = 'sale' if self.move_type == 'out_invoice' else 'purchase'
        for line in parsed_lines:
            # Strip a leading source/document reference such as "P00005: "
            raw_name = re.sub(
                r'^[A-Za-z]*\d+\s*[:\-]\s*', '', line['name']).strip()
            product_name, internal_reference = self._split_product_name(raw_name)
            product = self._find_or_create_product(
                product_name, internal_reference)
            if not product:
                continue
            values = {
                'move_id': self.id,
                'product_id': product.id,
                'quantity': line.get('quantity', 1.0),
                'price_unit': line.get('price_unit', 0.0),
            }
            tax = self._match_percentage_tax(line.get('tax'), tax_use)
            if tax:
                values['tax_ids'] = [Command.set(tax.ids)]
            self.env['account.move.line'].create(values)

    def _match_percentage_tax(self, percentage, tax_use):
        """Return a percentage tax matching ``percentage`` for ``tax_use``."""
        if not percentage:
            return self.env['account.tax']
        return self.env['account.tax'].search(
            [('type_tax_use', '=', tax_use),
             ('amount_type', '=', 'percent'),
             ('amount', '=', float(percentage))], limit=1)

    @staticmethod
    def _split_product_name(product_name):
        """Split a "[CODE] Name" string into ``(name, internal_reference)``."""
        parts = product_name.split('] ')
        if len(parts) > 1:
            return parts[1].strip(), parts[0].lstrip('[').strip()
        return product_name.strip(), None

    def _find_or_create_product(self, product_name, internal_reference):
        """Find a product by internal reference or barcode first, then by name,
        and create it only when the configuration allows automatic creation.

        Matching on a code/barcode rather than on the name alone avoids picking
        the wrong product when several share a similar label.
        """
        product = self.env['product.product']
        if internal_reference:
            product = product.search(
                [('default_code', '=', internal_reference)], limit=1) \
                or product.search(
                    [('default_code', 'ilike', internal_reference)], limit=1) \
                or product.search([('barcode', '=', internal_reference)], limit=1)
        if not product and product_name:
            product = product.search([('name', '=', product_name)], limit=1) \
                or product.search([('name', 'ilike', product_name)], limit=1)
        if (not product
                and self.invoice_digitization.product_creation_type == 'create_product'):
            values = {'name': product_name or internal_reference or _('OCR Product')}
            if internal_reference:
                values['default_code'] = internal_reference
            product = product.create(values)
        return product

    def _get_tax_ids(self, taxes, tax_per_invoice=False):
        """
        Retrieves the tax IDs for the given tax descriptions.
        """
        tax_records = self.env['account.tax']
        for tax in taxes:
            tax_record = self.env['account.tax'].search([
                ('active', '=', True),
                ('type_tax_use', '=',
                 'sale' if self.move_type == 'out_invoice' else 'purchase'),
                ('amount' if tax_per_invoice else 'name', '=', tax)
            ], limit=1)
            tax_records += tax_record
        return [(6, 0, tax_records.ids)] if tax_records else False

    def _process_pdf_using_ai(self, pdf_text):
        """
        Processes the provided PDF text using an AI endpoint to extract invoice data.

        Args:
            pdf_text (str): The text extracted from the PDF document.

        Updates the invoice record with the extracted partner and invoice data.
        """
        conversation_history = [
            {
                "role": "user",
                "content": """
                You are an AI tasked with extracting structured data from invoice text. The following extracted text
                comes from an invoice, and you must return the details in JSON format.

                Extracted Text:
                {extracted_text}

                Instructions:
                1. **Invoice-Issuing Company Details**: Extract the details of the company issuing the invoice in a
                   dictionary with these keys:
                   - "company_name": The name of the invoice-issuing company.
                   - "company_address": The address of the invoice-issuing company.
                   - "company_country": The country of the invoice-issuing company **only if available**.
                   - "company_state": The state of the invoice-issuing company **only if available**.
                   - "company_zip": The postal/zip code of the invoice-issuing company **only if available**.
                   - "company_city": The city of the invoice-issuing company **only if available**.

                2. **Partner Details**: Extract partner information in a dictionary with these keys:
                   - "parent_company": Extract the partner's parent company name if:
                     - Most of the time, the partner's parent company and partner name appear on the same line,
                       separated by a comma (e.g., "XYZ Limited, Justin").
                     - In some cases, the parent company name is explicitly labeled under a heading like "Company"
                       or "Company:" followed by the company name on the next line (e.g., "Company: XYZ Limited").
                   - "partner_name": Extract the partner's name (this is required).
                      - If only the partner name is available without a parent company name or other address details
                        (such as state, city, country, etc.), include only the partner's name and leave other
                        address details empty.
                      - **Note**: The partner's name will always be present, but if there is no parent company
                        name, ensure "partner_company" is empty. There will be no cases with only the parent
                        company name and no partner name.
                   - "country": Extract the partner's country **only** if it appears **after** the partner's name
                     and is **available**.
                   - "state": Extract the state **only** if it appears **after** the partner's name and is
                     **available**.
                   - "zip": Extract the postal/zip code **only** if it appears **after** the partner's name and is
                     **available**.
                   - "city": Extract the city **only** if it appears **after** the partner's name and is
                     **available**.
                   - "street": Extract the street address **only** if it appears **after** the partner's name and
                     is **available**.
                   - "tax_id": The partner's Tax ID (include only if present).

                   **Important Notes**:
                   - The invoice-issuing company's details are always located at the **top** of the invoice.
                   - **Do not** include any address, country, state, zip code, or other details from **before**
                     the partner's name.
                   - Partner details start **after** any invoice-issuing company details. Ensure that only the
                     address information that follows the partner's name is selected.
                   - If no country, state, or postal code is present **after** the partner's name, **leave those
                     fields empty** instead of using any details from earlier in the text.
                   - **Strictly avoid selecting any country, state, zip code, or address details that belong to
                     the invoice-issuing company**. Only details that are explicitly part of the partner’s address
                     should be included.
                   - If only the partner's name is present (e.g., "Brandon Freeman") without address details,
                     return just the name and leave other address fields empty.

                   Example of excluded details:

                   ABC Limited cads casdc cwaef Arunachal Pradesh AR India Azure Interior, Brandon Freeman
                   5647 FG st zurich 94545 GSTIN: US12345677
                   **Ignore** all details before "Azure Interior, Brandon Freeman" as they belong to the
                   invoice-issuing company. Only select details that follow the partner's name "Azure Interior,
                   Brandon Freeman", such as "5647 FG st", "zurich", and "94545".
                   "ABC Limited" and the following address lines belong to the invoice-issuing company and should
                   be ignored. Only "Azure Interior, Brandon Freeman" is the partner and should be included in
                   the JSON response.

                3. **Invoice Information**:
                    - "invoice_date": Extract the invoice date in the format MM/DD/YYYY.If the date is found in
                       any other format, convert it to MM/DD/YYYY.
                    - "due_date": Extract the due date in the format MM/DD/YYYY.If the date is found in any other
                       format, convert it to MM/DD/YYYY.
                    - "incoterm": Extract the incoterm mentioned in the invoice.
                    - "payment_terms": Extract the payment terms from the invoice.
                    - "payment_communication": Extract the correct payment reference or communication field
                      (avoid selecting unrelated words).
                    - "customer_reference": Extract the customer reference or invoice reference (avoid selecting
                      unrelated words)..

                4. **Invoice Order Line**: Extract the details of each product or service in the invoice order
                   lines as an array of dictionaries. Each dictionary should contain the following:
                    - "product_name": Extract the product name. If the product name is split across multiple lines,
                      capture it fully without including unrelated text (such as tax names).* If the product name
                      contains a product code/SKU in square brackets (e.g., "[FURN_7888] Desk Stand with Screen"),
                            include the ENTIRE text including the bracketed code: "[FURN_7888] Desk Stand with Screen"
                    - "quantity": Extract the product quantity.
                    - "unit_price": Extract the unit price of the product.
                    - "disc_percent": Extract the discount percentage if available. If not visible, omit this key.
                    - "taxes": Extract all applicable taxes for each product. These may include multiple entries
                      (e.g., 'GST 5%', 'TCS @0.1%'). Ensure that any tax details that appear on separate lines are
                      correctly associated with the product.
                    - "amount": Extract the total amount for each line item.
                    - "uom": If the invoice includes a unit of measure (e.g., "5 units", "6 dozen", "7kg"),
                      extract and include it in the dictionary. If no unit of measure is present, omit this key.

                5. **Total Tax Percentages**: Check for any tax percentage(s) applied on the total invoice amount.
                    - Extract each tax percentage separately if multiple tax percentages are applied (e.g.,
                      "Tax 15%", "Tax 10%").
                    - Add these percentages to the `total_tax_percentages` list.
                    - If no total tax percentage is specified, leave the list empty.
                6. **Currency Code**: Extract the currency code used in the invoice (e.g., "USD" for US dollars,
                   "EUR" for Euros).

                Ensure that the output is well-structured in JSON format and follows the instructions above. The JSON
                must not include any additional text.

                Example Output:
                {
                    "company": {
                        "company_name": "...",
                        "company_address": "...",
                        "company_country": "...",
                        "company_state": "...",
                        "company_zip": "...",
                        "company_city": "..."
                    },
                    "partner": {
                        "parent_company": "...",
                        "partner_name": "...",
                        "country": "",
                        "state": "",
                        "zip": "...",
                        "city": "...",
                        "street": "...",
                        "email": "...",
                        "phone": "..."
                    },
                    "invoice_date": "...",
                    "due_date": "...",
                    "incoterm": "...",
                    "payment_terms": "...",
                    "payment_communication": "...",
                    "customer_reference": "...",
                    "invoice_orderline": [
                        {
                            "product_name": "...",
                            "quantity": ...,
                            "uom": "...",
                            "unit_price": ...,
                            "disc_percent": ...,
                            "taxes": [...],
                            "amount": "..."
                        }
                    ],
                    "total_tax_percentages": [
                        // List of tax percentages applied on the total amount. Example: [15, 10]
                    ],
                    "currency_code": "..."
                }
                """
            }
        ]

        try:
            response = self.make_response_with_default(pdf_text,
                                                       conversation_history)
            data = json.loads(response["response"])
            payment_ref = data.get("payment_communication", "")
            def is_duplicated_text(value):
                if not value or len(value) % 2 != 0:
                    return False
                for i in range(0, len(value), 2):
                    if value[i] != value[i + 1]:
                        return False
                return True
            if is_duplicated_text(payment_ref):
                match = re.search(r'INV/\d{4}/\d+', pdf_text)
                if match:
                    data["payment_communication"] = match.group(0)
                else:
                    cleaned_ref = "".join(
                        payment_ref[i]
                        for i in range(0, len(payment_ref), 2)
                    )
                    if re.match(r'INV/\d{4}/\d+', cleaned_ref):
                        data["payment_communication"] = cleaned_ref
            matches = re.findall(r'[A-Z]+/\d+/\d+', pdf_text)
            if not response.get('is_error', False):
                partner = self._process_invoice_partner(data.get("partner"))
                if partner:
                    self.write({"partner_id": partner.id})
                self._process_invoice_data(data)
                self._process_invoice_order_line(
                    data.get("invoice_orderline"),
                    data.get("currency_code"),
                    data.get("total_tax_percentages")
                )
                self.ocr_digitize_completed = True
                self.ocr_digitize_failed = False
            else:
                self._mark_ocr_failed(response.get("response"))
        except Exception as e:
            _logger.error(f"Processing error: {e}")
            self._mark_ocr_failed("The AI Failed to Digitize the Document.")

    def _mark_ocr_failed(self, message):
        """
        Marks the OCR process as failed and logs the failure message.

        Args:
            message (str): The failure message to be recorded.
        """
        self.ocr_digitize_failed = True
        self.ocr_digitize_completed = False
        self.write({'ocr_digitize_message': _(message)})

    def make_response_with_default(self, pdf_text, conversation_history):
        """
        Sends the PDF text and conversation history to the AI endpoint for processing.

        Args:
            pdf_text (str): The text extracted from the PDF.
            conversation_history (list): Conversation history to send in the request.

        Returns:
            dict: A dictionary containing either the response data or an error message.
        """
        config_parameter = self.env['ir.config_parameter'].sudo()
        open_ai_key = config_parameter.get_param(
            "cyllo_invoice_digitization.digitization_openai_key", False)

        try:
            response = iap_tools.iap_jsonrpc(
                DEFAULT_OLG_ENDPOINT + "/api/olg/1/chat",
                params={
                    "prompt": pdf_text,
                    "conversation_history": conversation_history or [],
                    'version': release.version,
                },
                timeout=30,
            )
            if response["status"] == "success":
                return {"is_error": False, "response": response["content"]}
            return self._fallback_to_gpt(open_ai_key, pdf_text,
                                         conversation_history)
        except AccessError:
            return self._fallback_to_gpt(open_ai_key, pdf_text,
                                         conversation_history,
                                         "AI is unreachable.")
        except Exception as e:
            _logger.error(f"Unexpected error: {e}")
            return self._fallback_to_gpt(open_ai_key, pdf_text,
                                         conversation_history)

    def _handle_response_error(self, status, pdf_text, conversation_history,
                               open_ai_key):
        """
        Handles errors returned by the AI endpoint.
        """
        error_messages = {
            "error_prompt_too_long": "The AI model cannot process this large input at this time.",
            "limit_call_reached": "You've reached the maximum number of requests. Please try again later.",
        }
        error_message = error_messages.get(status,
                                           "Unable to generate a response.")
        return self._fallback_to_gpt(open_ai_key, pdf_text,
                                     conversation_history)

    def _fallback_to_gpt(self, api_key, prompt, conversation_history,
                         custom_message=None):
        """
        Fallback to GPT if the default AI endpoint fails.

        Args:
            api_key (str): The API key for GPT.
            prompt (str): The prompt text for GPT.
            conversation_history (list): The conversation history for GPT.
            custom_message (str, optional): Custom error message to use. Defaults to None.

        Returns:
            dict: A dictionary containing the GPT response or an error message.
        """
        response = self.make_response_with_gpt(api_key, prompt,
                                               conversation_history)
        if response.get('is_error', True):
            return {"is_error": True, "response": response[
                                                      'response'] or "Failed to generate response."}
        return response

    @staticmethod
    def make_response_with_gpt(api_key, prompt, conversation_history):
        """
        Generates a response using GPT as a fallback.

        Args:
            api_key (str): The API key for GPT.
            prompt (str): The prompt text for GPT.
            conversation_history (list): The conversation history for GPT.

        Returns:
            dict: A dictionary containing the GPT response or an error message.
        """
        try:
            client = OpenAI(api_key=api_key)
            messages = conversation_history + [
                {"role": "user", "content": prompt}]
            response = client.chat.completions.create(model=GPT_MODEL,
                                                      messages=messages,
                                                      temperature=0)
            return {"is_error": False,
                    "response": response.choices[0].message.content}
        except AuthenticationError:
            _logger.error("Invalid OpenAI API key.")
            return {"is_error": True, "response": "Invalid OpenAI API key."}
        except Exception as e:
            _logger.error(f"GPT fallback error: {e}")
            return {"is_error": True,
                    "response": "Error during fallback GPT request."}

    def _process_invoice_order_line(self, invoice_order_line, currency_code,
                                    total_taxes):
        """
        Processes the invoice_order_line by finding or creating products and generating account move lines.
        """
        taxes = None
        if self.invoice_digitization.tax_type == "tax_per_invoice" and len(
                total_taxes) > 0:
            taxes = self._get_tax_ids(total_taxes, tax_per_invoice=True)
        for order in invoice_order_line:
            product_name, internal_reference = self._split_product_name(
                order.get('product_name', ''))
            product_record = self._find_or_create_product(product_name,
                                                          internal_reference)
            if product_record:
                data = {
                    'move_id': self.id,
                    'product_id': product_record.id,
                    'quantity': order.get('quantity', 0),
                    'price_unit': self._process_currency_conversion(
                        order.get('unit_price', 0), currency_code),
                    'tax_ids': taxes if taxes else self._get_tax_ids(
                        order.get('taxes', [])),
                    'discount': order.get('disc_percent', 0.0),
                }
                self.env['account.move.line'].create(data)

    def _process_currency_conversion(self, amount, currency_code):
        """
        Converts an amount from a specified currency to the company's currency.
        """
        company_currency = self.env.company.currency_id
        source_currency = self.env['res.currency'].search([
            '|',
            ('name', '=', currency_code),
            ('symbol', '=', currency_code)
        ], limit=1)

        if not source_currency:
            return amount

        converted_amount = source_currency._convert(amount, company_currency)
        return converted_amount

    def _process_invoice_data(self, data):
        """
        Process and update invoice fields based on the provided data.

        This method updates various invoice fields (e.g., invoice date, due date, incoterm,
        payment terms, payment reference, and customer reference) if the corresponding
        keys are present in the input data dictionary.
        """
        if data.get("invoice_date"):
            date_object = self.parse_date(data["invoice_date"])
            if date_object:
                self.write({'invoice_date': date_object.strftime('%Y-%d-%m')})
            else:
                _logger.warning(
                    f"Failed to parse invoice date: {data['invoice_date']}.Invoice date not updated."
                )

        if data.get("due_date"):
            date_object = self.parse_date(data["due_date"])
            if date_object:
                self.write(
                    {'invoice_date_due': date_object.strftime('%Y-%d-%m')})
            else:
                _logger.warning(
                    f"Failed to parse due date: {data['due_date']}. "
                    "Due date not updated."
                )
        if data.get("incoterm"):
            incoterm = self.env['account.incoterms'].search([
                '|',
                ('code', '=', data["incoterm"]),
                ('name', '=', data["incoterm"])
            ], limit=1)
            self.write(
                {'invoice_incoterm_id': incoterm.id if incoterm else False})

        if data.get("payment_terms"):
            payment_term = self.env['account.payment.term'].search([
                ('name', '=', data["payment_terms"])
            ], limit=1)
            self.write(
                {'invoice_payment_term_id': payment_term.id if payment_term
                else False})

        if data.get("payment_communication"):
            self.write({'payment_reference': data["payment_communication"]})

        if data.get("customer_reference"):
            self.write({'ref': data["customer_reference"]})

    @staticmethod
    def parse_date(date_string):
        """Helper function to parse dates in multiple formats"""
        formats = [
            '%d/%m/%Y',  # European format
            '%m/%d/%Y',  # US format
            '%d. %B %Y',  # German format with full month name
            '%d.%m.%Y',  # German format with numbers
            '%Y-%m-%d'  # ISO format
        ]

        current_locale = locale.getlocale()[0]
        if 'de' in str(current_locale).lower():
            try:
                locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')
            except locale.Error:
                _logger.warning(
                    "Failed to set German locale. German date formats might not work correctly.")

        for date_format in formats:
            try:
                return datetime.strptime(date_string, date_format)
            except ValueError:
                continue

        _logger.warning(
            f"Could not parse date '{date_string}'. Supported formats: DD/MM/YYYY, "
            "MM/DD/YYYY, DD. Month YYYY, DD.MM.YYYY. Using default date."
        )
        return None

    def _process_invoice_partner(self, partner_details):
        """
        Processes the provided partner details and either finds or creates the partner or company.

        Args:
            partner_details (dict): Dictionary containing partner information, such as company name,
                                    partner name, address, state, country, and tax ID.

        Returns:
            res.partner: The matched or newly created partner record, or None if insufficient data is provided.
        """
        partner_details = dict(partner_details or {})
        if not partner_details:
            return None
        if not partner_details.get('partner_name'):
            for key in ('name', 'customer_name', 'vendor_name', 'supplier_name'):
                if partner_details.get(key):
                    partner_details['partner_name'] = partner_details[key]
                    break
        if (not partner_details.get('parent_company')
                and partner_details.get('partner_company')):
            partner_details['parent_company'] = partner_details['partner_company']
        for key in ('parent_company', 'partner_name', 'country', 'state',
                    'zip', 'city', 'street', 'tax_id'):
            if isinstance(partner_details.get(key), str):
                partner_details[key] = partner_details[key].strip()
        if partner_details.get('partner_name') and not partner_details.get(
                'parent_company'):
            if ',' in partner_details.get('partner_name'):
                parts = partner_details.get('partner_name').split(',', 1)
                partner_details['parent_company'] = parts[0].strip()
                partner_details['partner_name'] = parts[1].strip()
        if (partner_details.get('parent_company')
                and partner_details.get('partner_name')
                and partner_details['parent_company'].lower()
                == partner_details['partner_name'].lower()):
            partner_details['parent_company'] = ''

        if partner_details.get('parent_company') and not partner_details.get(
                'partner_name'):
            partner_details['partner_name'] = partner_details['parent_company']
            partner_details['parent_company'] = ''
        elif not partner_details.get(
                'parent_company') and not partner_details.get('partner_name'):
            return None

        parent_company, partner = self.find_partner_by_details(partner_details)

        data = {key: partner_details[key] for key in ['street', 'city', 'zip']
                if partner_details.get(key)}

        if partner_details.get('tax_id'):
            data['vat'] = partner_details.get('tax_id')

        if partner_details.get('state'):
            data['state_id'] = self.env['res.country.state'].search([
                '|', ('code', '=', partner_details['state']),
                ('name', '=', partner_details['state'])
            ], limit=1).id

        if partner_details.get('country'):
            data['country_id'] = self.env['res.country'].search(
                [('name', '=', partner_details['country'])], limit=1).id

        if partner_details.get('parent_company') and not parent_company:
            data['name'] = partner_details['parent_company']
            data['is_company'] = True
            parent_company = self.env['res.partner'].create(data)

        if not partner:
            data['name'] = partner_details['partner_name']
            if parent_company:
                data['parent_id'] = parent_company.id
                data['is_company'] = False
            partner = self.env['res.partner'].create(data)

        return partner

    def find_partner_by_details(self, partner_details):
        """
        Searches for a partner or company matching the given details.

        Args:
            partner_details (dict): Dictionary with partner or company details.

        Returns:
            tuple: (parent_company, partner), where `parent_company` is the matched company record or None,
                   and `partner` is the matched partner record or None.
        """
        partner = self.env['res.partner']

        if partner_details.get('parent_company'):
            parent_company = partner.search([
                ('name', '=', partner_details['parent_company']),
                ('is_company', '=', True)
            ])

            if parent_company:
                partner = partner.search(
                    [('name', '=ilike', partner_details['partner_name'])])
                partner_record = partner.filtered(
                    lambda p: p.parent_id.id in parent_company.ids)
                partner_record = self.filter_partners(partner_record,
                                                      partner_details)
                if len(partner_record) > 1:
                    partner_record = partner_record[0]
                return (partner_record.parent_id,
                        partner_record) if partner_record else (
                    parent_company[0], None)
            else:
                return None, None

        else:
            partner = partner.search(
                [('name', '=ilike', partner_details['partner_name'])])
            partner = self.filter_partners(partner, partner_details)
            return None, partner[0] if partner else None

    @staticmethod
    def filter_partners(partners, details):
        """
        Filters the partner records based on additional details like country, state, zip, city, and street.

        Args:
            partners (recordset): A recordset of potential matching partners.
            details (dict): Additional filtering criteria such as country, state, zip, city, and street.

        Returns:
            recordset: Filtered recordset of partners matching the criteria.
        """
        def normalize(value):
            return re.sub(r'[^a-z0-9]', '', str(value or '').lower())

        def filter_or_keep_unset(recordset, expected, value_getter, matcher):
            if not expected or not recordset:
                return recordset
            matching = recordset.filtered(
                lambda partner: value_getter(partner)
                and matcher(value_getter(partner), expected))
            if matching:
                return matching
            return recordset.filtered(lambda partner: not value_getter(partner))

        if details.get('tax_id'):
            tax_norm = normalize(details['tax_id'])
            partners = filter_or_keep_unset(
                partners,
                tax_norm,
                lambda p: p.vat,
                lambda value, expected: normalize(value) == expected)
        if details.get('country'):
            country = str(details['country']).lower()
            partners = filter_or_keep_unset(
                partners,
                country,
                lambda p: p.country_id.name if p.country_id else '',
                lambda value, expected: value.lower() == expected)
        if details.get('state'):
            state = str(details['state']).lower()
            partners = filter_or_keep_unset(
                partners,
                state,
                lambda p: (
                    f"{p.state_id.name or ''} {p.state_id.code or ''}"
                    if p.state_id else ''
                ),
                lambda value, expected: expected in value.lower()
            )
        if details.get('zip'):
            zip_value = normalize(details['zip'])
            partners = filter_or_keep_unset(
                partners,
                zip_value,
                lambda p: p.zip,
                lambda value, expected: normalize(value) == expected)
        if details.get('city'):
            city = str(details['city']).lower()
            partners = filter_or_keep_unset(
                partners,
                city,
                lambda p: p.city,
                lambda value, expected: value.lower() == expected)
        if details.get('street'):
            street_norm = normalize(details['street'])
            partners = filter_or_keep_unset(
                partners,
                street_norm,
                lambda p: ' '.join(filter(None, [p.street, p.street2])),
                lambda value, expected: (
                    expected in normalize(value)
                    or normalize(value) in expected
                ))
        return partners

    def _process_pdf_manually(self, file_path, text):
        """ Helper function to process PDF with manual digitization logic """
        try:
            with open(file_path, mode='rb') as pdf_data_file:
                pdf_data = pdf_data_file.read()
            # Temporarily store PDF data for Camelot to process
            with tempfile.NamedTemporaryFile(suffix='.pdf',
                                             delete=False) as temp_pdf_file:
                temp_pdf_file.write(pdf_data)
            # Extract tables using Camelot
            tables = camelot.read_pdf(temp_pdf_file.name,
                                      pages='all',
                                      backend='poppler')
            if not tables:
                tables = camelot.read_pdf(temp_pdf_file.name,
                                          flavor="stream",
                                          pages='all')
            combined_table = pd.concat([table.df for table in tables],
                                       ignore_index=True) \
                if len(tables) > 1 else tables[0].df
            # Process structured table data
            table_data = [
                [[item.replace('\xa0', ' ').strip() for item in row if
                  item.strip()] for row in table.df.itertuples(index=False)]
                for table in tables
            ]
            self.find_partner(text)
            self.action_find_field_values(text)
            invoice_line_column_values = self.action_get_invoice_line_columns(
                combined_table, text)
            ocr_products = self.action_create_products(
                combined_table,
                invoice_line_column_values)
            self.get_order_line(table_data, invoice_line_column_values)
            if self.ocr_digitize_failed:
                for product in ocr_products:
                    product.id.unlink()
        except Exception as e:
            _logger.error(f"Error during manual processing: {e}")
            raise

    def _process_pdf_ai(self, text, pdf_details):
        """ Helper function for AI-based PDF processing """
        invoice_details = self.get_invoice_details(
            pdf_details) if pdf_details else None
        product_details = self.get_product_details(
            pdf_details) if pdf_details else None
        self.find_partner_ai(text, invoice_details)
        self.get_invoice_date_ai(text, invoice_details)
        self.action_find_field_values_ai(invoice_details, text)
        self.action_find_product(product_details)

    @staticmethod
    def _norm_alnum(value):
        """Lower-case alphanumeric-only form of a string, for fuzzy compares."""
        return re.sub(r'[^a-z0-9]', '', (value or '').lower())

    def _detect_counterparty_block(self, text, company):
        """Return the counterparty address block (vendor/customer) as a dict
        ``{name, vat, street, zip}`` or ``None``.

        Every address block on the document is examined; the first block whose
        address and name are NOT our own company is returned. A block is "ours"
        when its ZIP or street matches the company address, or its name starts
        with the company's core name token (e.g. "Acme Corporation" while the
        company is "Acme Inc").
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        comp_partner = company.partner_id
        comp_zip = (comp_partner.zip or '').strip()
        comp_street = self._norm_alnum(comp_partner.street)[:12]
        comp_core = re.sub(
            r'(inc|ltd|llc|corp|corporation|co|company|gmbh|pvt|limited|plc|sa|bv)',
            '', self._norm_alnum(company.name))
        street_re = re.compile(r'^\d+[\s,]+\D')
        zip_re = re.compile(r'\b(\d{4,6})\b')
        vat_re = re.compile(
            r'(?:tin|tax\s*id|vat|gstin|abn|uid)\s*[:#]?\s*([A-Za-z0-9\-]{5,})',
            re.I)
        reject = ('description', 'quantity', 'unit price', 'amount', 'total',
                  'tax', 'date', 'source', 'vendor bill', 'invoice', 'page',
                  'subtotal')
        for index, line in enumerate(lines):
            if index < 1 or not street_re.match(line):
                continue
            name = lines[index - 1].strip().rstrip(',').strip()
            if (street_re.match(name) or re.search(r'\d{3,}', name)
                    or len(name) < 3
                    or any(word in name.lower() for word in reject)):
                continue
            window = lines[index - 1:index + 5]
            block = ' '.join(window).lower()
            zip_match = zip_re.search(' '.join(lines[index:index + 3]))
            block_zip = zip_match.group(1) if zip_match else ''
            is_ours = (
                (comp_zip and block_zip and block_zip == comp_zip)
                or (comp_street and comp_street in self._norm_alnum(line))
                or (comp_core and len(comp_core) >= 3
                    and self._norm_alnum(name).startswith(comp_core)))
            if is_ours:
                continue
            vat_match = next(
                (vat_re.search(text_line) for text_line in window
                 if vat_re.search(text_line)), None)
            return {
                'name': name.split(',')[0].strip(),
                'vat': vat_match.group(1) if vat_match else False,
                'street': line,
                'zip': block_zip,
            }
        return None

    def _match_partner_from_block(self, partners, block):
        """Return the best existing partner for a detected counterparty block.

        Combines name and VAT so neither alone drives the match: an exact name
        wins first; otherwise the VAT is used (narrowed by name when several
        partners share a VAT, as happens with demo data); finally a loose name
        match. Returns an empty recordset when nothing matches.
        """
        name = (block.get('name') or '').lower()
        vat_norm = self._norm_alnum(block.get('vat'))
        if name:
            exact = partners.filtered(lambda p: p.name and p.name.lower() == name)
            if exact:
                return exact[:1]
        if vat_norm:
            by_vat = partners.filtered(
                lambda p: p.vat and self._norm_alnum(p.vat) == vat_norm)
            if len(by_vat) > 1 and name:
                by_vat = by_vat.filtered(
                    lambda p: name in p.name.lower()
                    or p.name.lower() in name) or by_vat
            if by_vat:
                return by_vat[:1]
        if name:
            loose = partners.filtered(
                lambda p: p.name and (name in p.name.lower()
                                      or p.name.lower() in name))
            if loose:
                return loose.sorted(
                    key=lambda p: (p.is_company, len(p.name or '')),
                    reverse=True)[:1]
        return partners.browse()

    def find_partner(self, text):
        """Identify and set the document's counterparty.

        Order of preference: (1) the non-company address block, matched to an
        existing partner by name and VAT (see ``_match_partner_from_block``)
        and created when missing; (2) the best existing partner whose name
        appears in the text; (3) AI extraction as a last resort.
        """
        company_partner = self.env.company.partner_id
        company_name = (self.env.company.name or '').lower()
        domain = [('id', '!=', company_partner.id)] if company_partner else []
        partners = self.env['res.partner'].search(domain)

        block = self._detect_counterparty_block(text, self.env.company)
        if block:
            partner = self._match_partner_from_block(partners, block)
            if not partner:
                values = {'name': block['name'], 'is_company': True}
                if block['vat']:
                    values['vat'] = block['vat']
                if block['street']:
                    values['street'] = block['street']
                partner = self.env['res.partner'].create(values)
            self.partner_id = partner.id
            return

        matches = partners.filtered(
            lambda p: p.name and p.name.lower() != company_name
            and p.name.lower() in text.lower())
        if matches:
            self.partner_id = matches.sorted(
                key=lambda p: (p.is_company, len(p.name or '')),
                reverse=True)[0].id
            return

        self._create_partner_from_text(text)

    def _create_partner_from_text(self, text):
        """
        Create a new partner based on the extracted partner details from the text.
        :param text: Extracted text to infer partner details.
        """
        partner_details = self.get_partner_details_ai(text)
        if not partner_details:
            return
        partner_name = partner_details.get('partner_name')
        if partner_name:
            state_name = partner_details.get('state')
            state = self.env['res.country.state'].search(
                [('name', '=', state_name)])
            new_partner_vals = {
                'name': partner_name,
                'street': partner_details.get('street', ''),
                'city': partner_details.get('city', ''),
            }
            if state:
                new_partner_vals['state_id'] = state.id
            # Create the new partner
            new_found_partner = self.env['res.partner'].create(new_partner_vals)
            # Assign the newly created partner to the record
            self.write({'partner_id': new_found_partner.id})

    def get_partner_details_ai(self, text):
        """
        Retrieve partner details from an AI service based on the provided text.
        Args:
            text (str): The text to be analyzed for partner details.
        Returns:
            dict: A dictionary containing partner details such as name,
            street, city, state, and country. If values are null,
            corresponding keys are assigned blank values. The response
            strictly follows the specified guidelines and does not contain
            any additional text. If extraction fails, returns an empty
            dictionary.
        """
        try:
            company_name = self.env.company.name
            conversation_history = [
                {
                    'role': 'user',
                    'content': (
                        f"Find partner details from this invoice or bill like "
                        f"customer name and address of the customer. When extracting "
                        f"the customer name, consider the person billed to and do not "
                        f"include {company_name}. The dictionary keys should correspond "
                        f"to partner_name, street, city, state, country. If the values "
                        f"are null, assign a blank value to the corresponding key. The "
                        f"response should only contain the dictionary without any additional "
                        f"text and do not add new line commands or unwanted spaces. (It must "
                        f"strictly follow these guidelines)."
                    )
                }
            ]
            # Fetching config parameter once
            config_parameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = config_parameter.get_param(
                'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT
            )
            # Making the API call
            response = iap_tools.iap_jsonrpc(
                f"{olg_api_endpoint}/api/olg/1/chat",
                params={
                    'prompt': text,
                    'conversation_history': conversation_history,
                    'version': release.version,
                },
                timeout=30
            )
            # If response is successful, handle the JSON decoding
            if response.get('status') == 'success':
                content = response.get('content', '{}')
                try:
                    partner_details = json.loads(content)
                except json.JSONDecodeError:
                    start_index = response['content'].find("{")
                    end_index = response['content'].find("}")
                    # Extract the substring containing the list
                    extracted_invoice_details = response['content'][
                        start_index:end_index + 1]
                    partner_details = json.loads(extracted_invoice_details)
                return partner_details
            # Handle error conditions
            self._mark_ocr_failure("Failed to Identify the Customer")
        except json.JSONDecodeError as json_exc:
            _logger.error(f"JSON decoding error: {json_exc}")
            self._mark_ocr_failure("Failed to Identify the Customer")
        except TimeoutError as timeout_exc:
            _logger.error(f"Timeout error: {timeout_exc}")
            self._mark_ocr_failure(
                "Request timed out. Could not retrieve details.")
        except Exception as exc:
            _logger.error(f"AccessError details: {exc}")
            self._mark_ocr_failure("Failed to Identify the Customer")

    def _mark_ocr_failure(self, message):
        """
        Helper function to mark OCR as failed and log the error message.
        """
        self.ocr_digitize_failed = True
        self.ocr_digitize_completed = False
        self.write({'ocr_digitize_message': _(message)})

    def action_find_field_values(self, text):
        """
        Find and update field values in the invoice based on the provided text.
        :param text: Text content to extract field values from.
        """
        # Retrieve invoice digitization settings (with fallback to any active)
        invoice_digitization = self.invoice_digitization
        if not invoice_digitization.invoice_field_details_ids:
            return
        window_size = 50  # Standard window size for searching after a keyword
        for field in invoice_digitization.invoice_field_details_ids:
            for keyword in field.field_keyword_ids:
                keyword_pattern = rf'({re.escape(keyword.name.lower())})'
                keyword_match = re.search(keyword_pattern, text.lower())
                if not keyword_match:
                    continue
                keyword_start = keyword_match.start()
                text_window = text[keyword_start:keyword_start + window_size]
                if field.invoice_field_id.ttype == 'date':
                    self._handle_date_field(text_window, field, text)
                elif field.invoice_field_id.ttype == 'char':
                    # The value usually follows the keyword, possibly on the
                    # next line, e.g. "Source:\nP00005" -> "P00005".
                    after = text_window
                    index = after.lower().find(keyword.name.lower())
                    if index != -1:
                        after = after[index + len(keyword.name):]
                    tokens = [token for token in re.split(r'[\s:]+', after)
                              if token]
                    if tokens:
                        self[field.invoice_field_id.name] = tokens[0]

    def _handle_date_field(self, text_window, field, text):
        """Handles the extraction and processing of date fields."""
        date_pattern = r'\d{1,2}/\d{1,2}/\d{2,4}'
        dates_near_keyword = re.findall(date_pattern, text_window)
        field_values = []
        field_values.extend(dates_near_keyword)
        user_date_format = self.env['res.lang']._lang_get(
            self.env.user.lang).date_format
        if dates_near_keyword:
            valid_dates = []
            for date in dates_near_keyword:
                try:
                    datetime.strptime(date, user_date_format)
                    valid_dates.append(date)
                except ValueError:
                    try:
                        formatted_date = datetime.strptime(
                            date,
                            '%d/%m/%Y').strftime(
                            user_date_format)
                        valid_dates.append(formatted_date)
                    except ValueError:
                        valid_dates.append(date)
            sorted_dates = sorted(
                [datetime.strptime(date, user_date_format) for date in
                 valid_dates]
            )
            if sorted_dates:
                # Update the invoice fields based on the type
                if field.invoice_field_id.name == 'invoice_date':
                    self.write({'invoice_date': sorted_dates[0]})
                elif field.invoice_field_id.name == 'invoice_date_due' and len(
                        sorted_dates) == 1:
                    self.write({'invoice_date_due': sorted_dates[0]})
                elif field.invoice_field_id.name == 'invoice_date_due' and len(
                        sorted_dates) > 1:
                    self.write({'invoice_date_due': sorted_dates[1]})
                else:
                    self.write({field.invoice_field_id.name: sorted_dates[0]})

        # Handle fallback for date fields if no matches are found
        if not field_values:
            self.get_invoice_date(text, field.invoice_field_id.name)

    def get_invoice_date(self, text, field_name):
        """
        Extract and set the invoice date or due date from the given text.
        :param text: The text to extract dates from.
        :param field_name: The field name to update.
        """
        # Define a regular expression for date patterns (DD/MM/YYYY)
        date_pattern = r'\b\d{2}/\d{2}/\d{4}\b'
        extracted_dates = re.findall(date_pattern, text)
        user_date_format = self.env['res.lang']._lang_get(
            self.env.user.lang).date_format
        # Attempt to parse valid dates and log any errors
        valid_dates = []
        for date in extracted_dates:
            try:
                formatted_date = datetime.strptime(date, '%d/%m/%Y').strftime(
                    user_date_format)
                valid_dates.append(formatted_date)
            except ValueError:
                valid_dates.append(date)
        # Process valid dates
        if len(valid_dates) == 1:
            # Only one date found
            if field_name == 'invoice_date':
                self.write({'invoice_date': valid_dates[0]})
            else:
                _logger.warning(
                    f"Unexpected field name for a single date: {field_name}")
        elif len(valid_dates) == 2:
            # Two dates found, sorting and assigning to the correct fields
            sorted_dates = sorted(valid_dates)
            if field_name == 'invoice_date':
                self.write({'invoice_date': sorted_dates[0]})
            if field_name == 'invoice_date_due':
                self.write({'invoice_date_due': sorted_dates[1]})
        else:
            _logger.warning(
                f"Expected 1 or 2 dates, but found {len(valid_dates)}.")

    def _handle_char_field(self, text_window, keyword, field):
        """Handles the extraction of char fields based on keyword."""
        char_text_window = text_window[:40]
        keyword_split = keyword.name.split()
        if len(keyword_split) > 1:
            # Adjust window to capture text after second word of keyword
            keyword_pattern = rf'({re.escape(keyword_split[1].lower())})'
            match = re.search(keyword_pattern, char_text_window.lower())
            if match:
                keyword_split_start = match.start()
                char_text_window = char_text_window[
                    keyword_split_start:keyword_split_start + 40]
        # Extract the word after the keyword
        split_char_text_window = char_text_window.split()
        if len(split_char_text_window) > 1:
            extracted_word = split_char_text_window[1]
            self.write({field.invoice_field_id.name: extracted_word})

    def _handle_many2one_field(self, text, text_window, field):
        """Handles the extraction of many2one fields based on the text."""
        model_name = field.invoice_field_id.relation
        if model_name == 'res.partner':
            return
        records = self.env[model_name].search([])
        found_records = [rec for rec in records if
                         rec.name.lower() in text_window.lower() or rec.name.lower() in text.lower()]
        if found_records:
            self.write({field.invoice_field_id.name: found_records[0].id})
        # Special handling for 'invoice_incoterm_id'
        if field.invoice_field_id.name == 'invoice_incoterm_id':
            incoterm_records = [rec for rec in records if
                                rec.code in text_window or rec.code in text]
            if incoterm_records:
                self.write(
                    {field.invoice_field_id.name: incoterm_records[0].id})

    def action_get_invoice_line_columns(self, combined_table, text):
        """
        Extracts relevant details from a combined table based on configured
        keywords for invoice digitization.
        Note:
            This method relies on configured keywords and field mappings for
            extracting details such as quantity, tax, discount, and price unit
            from the given combined_table and associated text.

            The extracted values are returned in a dictionary format for further
            processing in the invoice digitization workflow.
        """
        invoice_digitization = self.env['invoice.digitization'].search(
            [('active_configuration', '=', True),
             ('account_type', '=', self.move_type)])
        invoice_line_values = {}
        if not combined_table.empty:
            for col in combined_table.columns:
                if invoice_digitization.invoice_line_field_details_ids:
                    for field in \
                            invoice_digitization.invoice_line_field_details_ids:
                        for keyword in field.line_field_keyword_ids:
                            column_values = combined_table[col].tolist()
                            column_values = [str(item).replace(
                                '\n',
                                ' ') for item in column_values]
                            column_values = [str(item).replace(
                                '\xa0',
                                ' ') for item in column_values]
                            cleaned_column_values = [item for item in
                                                     column_values
                                                     if item.strip() != '']
                            if any(keyword.name.lower() in str(val).lower()
                                   for val in column_values):
                                values_after_keyword = []
                                for val in cleaned_column_values:
                                    if keyword.name.lower() in val.lower():
                                        keyword_index = \
                                            cleaned_column_values.index(val)
                                        values_after_keyword \
                                            = cleaned_column_values[
                                            keyword_index + 1:]
                                        if (field.invoice_line_field_id.name
                                                == 'quantity'):
                                            column_values_copy = \
                                                values_after_keyword.copy()
                                            unit_of_measures = self.env[
                                                'uom.uom'].search([])
                                            currency_symbol = self.env[
                                                'res.currency'].search([])
                                            for unit in unit_of_measures:
                                                for currency in currency_symbol:
                                                    for value in \
                                                            column_values_copy:
                                                        split_value = str(
                                                            value).split()
                                                        for split in \
                                                                split_value:
                                                            if unit.name.lower() == split.lower():
                                                                (split_value.
                                                                 remove(split))
                                                                values_after_keyword.remove(
                                                                    value)
                                                                values_after_keyword.append(
                                                                    split_value[
                                                                        0])
                                                            if (currency.symbol
                                                                    == split):
                                                                if value in values_after_keyword:
                                                                    values_after_keyword.remove(
                                                                        value)
                                            extracted_numbers = []
                                            for item in values_after_keyword:
                                                # Use regular expression to find numeric values
                                                numeric_values = re.findall(
                                                    r'\b\d+\.*\d*\b(?!\%)',
                                                    item)
                                                for value in numeric_values:
                                                    # Check if the numeric value is not associated with a string
                                                    if not any(
                                                            char.isalpha()
                                                            for char in
                                                            item):
                                                        (extracted_numbers.
                                                         append(value))
                                            values_after_keyword = list(
                                                set(extracted_numbers))
                                        elif (field.invoice_line_field_id.name
                                              == 'tax_ids'):
                                            if (invoice_digitization.tax_type
                                                    == 'tax_per_line'):
                                                split_tax_column = \
                                                    [val for value in
                                                     values_after_keyword for
                                                     val in value.split()]
                                                percentage_numbers = (
                                                    re.findall(
                                                        r'\d+(?:\.\d+)?%',
                                                        str(split_tax_column)))
                                                if len(percentage_numbers) <= 1:
                                                    percentage_numbers = self.find_tax_values(
                                                        combined_table)
                                                    values_after_keyword = percentage_numbers
                                                else:
                                                    values_after_keyword = \
                                                        percentage_numbers
                                            else:
                                                values_after_keyword = self.find_tax_per_invoice(
                                                    keyword, text)
                                        elif (field.invoice_line_field_id.name
                                              == 'discount'):
                                            split_values = \
                                                [item.split() for item in
                                                 values_after_keyword]
                                            flattened_list = [item for sublist
                                                              in split_values
                                                              for
                                                              item in sublist]
                                            filtered_list = [disc for disc in
                                                             flattened_list if
                                                             '%' not in disc]
                                            values_after_keyword = filtered_list
                                        elif (field.invoice_line_field_id.name
                                              == 'price_unit'):
                                            values_after_keyword = [
                                                val.replace(',', '') for val in
                                                values_after_keyword]
                                            filtered_values_after_keyword = []
                                            for values in values_after_keyword:
                                                if not any(
                                                        val.isalpha() for val in
                                                        values):
                                                    filtered_values_after_keyword.append(
                                                        values)
                                            split_values_after_keyword = [val
                                                                          for value in filtered_values_after_keyword
                                                                          for val in value.split()
                                                                          if not re.search(
                                                    r'\d+%',
                                                    val)]
                                            price_pattern = \
                                                r'(\d+(\.\d{1,2})?)(?![\d%]*%)'
                                            prices = []
                                            for split_val in \
                                                    split_values_after_keyword:
                                                price_match = re.match(
                                                    price_pattern, split_val)
                                                if price_match:
                                                    price = float(
                                                        price_match.group())
                                                    prices.append(price)
                                                else:
                                                    if not any(
                                                            char.isalpha() for
                                                            char in split_val):
                                                        split_val = ''.join(
                                                            char for char in
                                                            split_val
                                                            if
                                                            char.isdigit() or
                                                            char == '.')
                                                        prices.append(split_val)
                                            prices = [item for item in prices if
                                                      item != '']
                                            values_after_keyword = prices
                                if values_after_keyword:
                                    invoice_line_values[
                                        field.invoice_line_field_id.name] = \
                                        values_after_keyword
                                else:
                                    invoice_line_values[
                                        field.invoice_line_field_id.name] = \
                                        cleaned_column_values
                                break  # Stop searching once the column is found
                            if (invoice_digitization.tax_type
                                    == 'tax_per_invoice'):
                                if (field.invoice_line_field_id.name
                                        == 'tax_ids'):
                                    values_after_keyword = self.find_tax_per_invoice(
                                        keyword, text)
                                    invoice_line_values[
                                        field.invoice_line_field_id.name
                                    ] = values_after_keyword
        return invoice_line_values

    def find_tax_values(self, combined_table):
        """
            Identify and extract the percentage values (e.g., "5%", "12.5%")
            from the column in the given table that contains the highest
            number of percentage entries.

            Args:
                combined_table (pandas.DataFrame): The table containing multiple
                    columns of tax-related data.

            Returns:
                list: A list of percentage strings (e.g., ["5%", "12.5%"])
                found in the column with the maximum number of percentage values.
            """
        # Initialize variables to track the column with the highest percentage count
        max_percentage_numbers = []
        for col in combined_table.columns:
            column_values = combined_table[col].tolist()
            column_values = [str(item).replace(
                '\n',
                ' ') for item in column_values]
            column_values = [str(item).replace(
                '\xa0',
                ' ') for item in column_values]
            cleaned_column_values = [item for item in column_values
                                     if item.strip() != '']
            split_tax_column = [val for value in cleaned_column_values for val
                                in value.split()]
            # Extract percentage values from the split column
            percentage_numbers = re.findall(r'\d+(?:\.\d+)?%',
                                            str(split_tax_column))
            # Update the column with the highest number of percentage values
            if len(percentage_numbers) > len(max_percentage_numbers):
                max_percentage_numbers = percentage_numbers
        return max_percentage_numbers

    def find_tax_per_invoice(self, keyword, text):
        """
           Search for percentage values (e.g., "5%", "18%") near a given keyword
           within an invoice text.

           The function first looks for the keyword in the text. If found, it extracts
           a window of characters following the keyword and searches within that
           window for percentage values. If no percentages are found in the window,
           it searches the entire text.

           Args:
               keyword (recordset/obj): An object with a `name` attribute representing
                   the keyword to search for (e.g., "GST", "VAT").
               text (str): The full invoice text to search in.

           Returns:
               list: A list of percentage strings (e.g., ["5%", "18%"]) found
               near the keyword or in the entire text. Returns an empty list if
               no percentages are found.
        """
        keyword_pattern = rf'({re.escape(keyword.name.lower())})'
        keyword_match = re.search(keyword_pattern, text.lower())
        if keyword_match:
            # Get the start position of the match
            keyword_start = keyword_match.start()
            window_size = 45
            text_window = text[keyword_start:keyword_start + window_size]
            percentage_numbers = (
                re.findall(r'\d+(?:\.\d+)?%', str(text_window)))
            if not percentage_numbers:
                percentage_numbers = re.findall(r'\d+(?:\.\d+)?%', text)
            return percentage_numbers or []

    def get_order_line(self, table_data, invoice_line_column_values):
        """
        Create order lines based on extracted table data.
        :param table_data: Structured table data extracted from the PDF.
        :param invoice_line_column_values: Values extracted from the table data.
        """
        product_ids = self.env['product.product'].search_read(
            [], ['name', 'default_code', 'lst_price', 'display_name',
                 'standard_price'])
        for product in product_ids:
            product['tax_ids'] = None
        # Find products in the table data based on name, code, or display name
        found_products_with_display_name = [product for data in table_data
                                            for row in data
                                            for product in product_ids
                                            if product['display_name'] in
                                            str(row)]
        cleaned_table_data = [
            [[item.replace('\n', '') for item in row] for row in data] for data
            in table_data]
        table_data_copy = cleaned_table_data.copy()
        new_table_data = [[row for row in data if all(
            product['display_name'] not in str(row) for product in product_ids)]
                          for data in table_data_copy]
        found_products_with_name = [product for data in new_table_data
                                    for row in data
                                    for product in product_ids if
                                    product['name'] in str(row)]
        found_products_with_all_name = (
                found_products_with_display_name +
                [item for item in found_products_with_name if item['id'] not in
                 {value['id'] for value in found_products_with_display_name}])
        found_display_name_rows = [row for data in cleaned_table_data
                                   for row in data
                                   for product in product_ids if
                                   product['display_name'] in str(row)]
        found_name_rows = [row for data in cleaned_table_data for row in data
                           for product in product_ids if
                           product['name'] in str(row)]
        found_all_name_rows = [list(sublist) for sublist in
                               set(tuple(sublist) for sublist in
                                   found_display_name_rows + found_name_rows)]
        found_products_with_code = [product for data in cleaned_table_data
                                    for row in data
                                    for product in product_ids if
                                    str(product['default_code']) in str(row)]
        found_code_rows = [row for data in cleaned_table_data for row in data
                           for product in product_ids if
                           str(product['default_code']) in str(row)]
        products_with_code_ids = {product['id'] for product in
                                  found_products_with_code}
        filtered_products_with_name = [rec for rec in
                                       found_products_with_all_name
                                       if
                                       rec['id'] not in products_with_code_ids]
        filtered_products_with_code = [rec for rec in found_products_with_code
                                       for row in found_code_rows if
                                       rec['name'] in str(row)]
        filtered_products_with_code = [product for index, product in
                                       enumerate(filtered_products_with_code)
                                       if product
                                       not in filtered_products_with_code[
                                           :index]]
        filtered_found_code_rows = [row for rec in found_products_with_code for
                                    row in found_code_rows if
                                    rec['name'] in str(row)]
        filtered_found_code_rows_set = set(
            tuple(row) for row in filtered_found_code_rows)
        filtered_found_name_rows = [row for row in found_all_name_rows if
                                    tuple(row)
                                    not in filtered_found_code_rows_set]
        filtered_found_name_rows = set(
            tuple(row) for row in filtered_found_name_rows)
        if not filtered_found_name_rows:
            actual_products = filtered_products_with_code
            actual_rows = filtered_found_code_rows_set
        else:
            actual_products = (filtered_products_with_code
                               + filtered_products_with_name)
            actual_rows = (filtered_found_code_rows_set
                           | filtered_found_name_rows)
        # Replace "\n" with a space in strings in actual_rows
        actual_rows = {tuple(cell.replace('\n', ' ') for cell in row) for
                       row in actual_rows}
        actual_rows = {tuple(cell.replace(',', '') for cell in row) for
                       row in actual_rows}
        # Create final invoice lines based on found products and rows
        if not actual_products:
            self.ocr_digitize_failed = True
            self.ocr_digitize_completed = False
            self.write({
                'ocr_digitize_message': _(
                    "Data cannot be read. Digitization failed.")
            })
            return
        final_invoice_lines = []
        for product in actual_products:
            # Use a helper function to match the product more efficiently
            matched_row = self.is_matching_product(product, actual_rows)
            final_product_price = self.find_product_price(
                product,
                matched_row,
                invoice_line_column_values) or {}
            final_product_qty = self.find_product_quantity(
                product,
                matched_row,
                invoice_line_column_values) or {}
            final_product_tax = self.find_product_tax(
                product,
                matched_row,
                invoice_line_column_values) or {}
            final_product_discount = self.find_product_discount(
                product,
                matched_row,
                invoice_line_column_values) or {}
            # Use default values if any field is missing
            quantity = float(final_product_qty.get('quantity', 1.0))
            price_unit = final_product_price.get(
                'lst_price', 0.0) if self.move_type == 'out_invoice' else (
                final_product_price.get(
                    'standard_price', 0.0))
            tax_ids = final_product_tax.get('tax_ids', [])
            discount = final_product_discount.get('discount', 0.0)
            invoice_line = {
                'move_id': self.id,
                'product_id': product['id'],
                'quantity': quantity,
                'price_unit': price_unit,
                'tax_ids': tax_ids,
                'discount': discount
            }
            final_invoice_lines.append(invoice_line)
        # Batch create invoice lines to optimize performance
        if final_invoice_lines:
            self.invoice_line_ids.create(final_invoice_lines)
            self.ocr_digitize_completed = True
            self.ocr_digitize_failed = False

    def is_matching_product(self, product, matched_row):
        """Helper function to improve readability and performance."""
        for row in matched_row:
            if (str(product['default_code']) in str(row) or
                    product['display_name'].replace(',', '') in str(row) or
                    str(row) in product['display_name']):
                return row

    def find_product_price(self, product, row, invoice_line_column_values):
        """
        Update the product price based on the extracted row and values.
        :param product: Product information.
        :param row: Extracted row from the table.
        :param invoice_line_column_values: Values extracted from the table data.
        :return: Updated product information.
        """
        # Split the row into items and filter out percentage values
        split_row = [rec for item in row for rec in item.split() if
                     not re.search(r'\d+%', rec)]
        new_split_row = []
        for item in split_row:
            # Check if the item contains a value like '5.00300.00'
            if isinstance(item, str) and '.' in item:
                parts = item.split('.')
                if len(parts) > 2:  # This indicates there are multiple dots, so we should split
                    # Split the value as requested
                    first_number = float(parts[0] + '.00')
                    second_number = float(parts[1] + '.' + parts[2])
                    # Add the two new values to the new list
                    new_split_row.append(str(first_number))
                    new_split_row.append(str(second_number))
                else:
                    # If it's a valid float already, just add it to the new list
                    new_split_row.append(item)
            else:
                # For all other cases, add the item as is
                new_split_row.append(item)
        price_pattern = r'(\d+(\.\d{1,2})?)(?![\d%]*%)'
        prices = []
        # Extract prices from the row
        for val in new_split_row:
            price_match = re.match(price_pattern, val)
            if price_match:
                price = float(price_match.group())
                prices.append(price)
            else:
                if not any(char.isalpha() for char in val):
                    val = ''.join(char for char in val if
                                  char.isdigit() or char == '.')
                    prices.append(val)
        prices = [item for item in prices if item != '']
        product_price = '0'
        if self.move_type == 'out_invoice':
            product_price = str(product['lst_price']) if product[
                'lst_price'] else '0'
        elif self.move_type == 'in_invoice':
            product_price = str(product['standard_price']) if product[
                'standard_price'] else '0'
        max_decimal_places = max(
            len(str(price).split('.')[1]) if '.' in str(price) else 0 for price
            in prices) if prices else None
        formatted_product_price = "{:.{dp}f}".format(float(product_price),
                                                     dp=max_decimal_places)
        # Update the product price based on matches with extracted prices
        matched_price = None

        # 1. Prioritize price from invoice_line_column_values if it intersects with row prices
        if 'price_unit' in invoice_line_column_values.keys():
            col_prices = invoice_line_column_values['price_unit']
            # Convert to float for safe comparison
            col_prices_float = []
            for cp in col_prices:
                try:
                    col_prices_float.append(float(cp))
                except ValueError:
                    pass
            common_price = [p for p in prices if p in col_prices_float]
            if common_price:
                matched_price = common_price[0]

        # 2. If no match from columns, check if the product's default price is in the row
        if matched_price is None:
            if float(product_price) in prices:
                matched_price = float(product_price)

        # 3. Fallback to the closest price to the default price
        if matched_price is None and prices:
            closest_price = min(prices, key=lambda x: abs(float(x) - float(product_price)))
            matched_price = closest_price

        if matched_price is not None:
            if self.move_type == 'out_invoice':
                product['lst_price'] = matched_price
            elif self.move_type == 'in_invoice':
                product['standard_price'] = matched_price
        return product

    def find_product_quantity(self, product, row, invoice_line_column_values):
        """
        Update the product quantity based on the extracted row and values.
        :param product: Product information.
        :param row: Extracted row from the table.
        :param invoice_line_column_values: Values extracted from the table data.
        :return: Updated product information.
        """
        row = list(row)
        # Remove currency symbols from the row
        currency_symbols = set(
            currency.symbol for currency in self.env['res.currency'].search([]))
        row = [value for value in row if not any(
            currency_symbol in str(value).split() for currency_symbol in
            currency_symbols)]
        row = [value for value in str(row).split() if "%" not in value]
        # Find quantity matches in the row
        quantity_match = re.findall(
            r'\b(\d+(\.\d{1,2})?)(?![%])\b', str(row))
        filtered_quantity = []
        for match in quantity_match:
            filtered_quantity += (
                tuple(item for item in match if
                      item != '' and not item.startswith(
                          '.')))
        # Clean up filtered_quantity from default_code
        filtered_quantity = [qty for qty in filtered_quantity if str(qty) != product.get('default_code')]

        matched_qty = None

        # 1. Prioritize quantity from invoice_line_column_values
        if 'quantity' in invoice_line_column_values.keys():
            col_qty = invoice_line_column_values['quantity']
            col_qty_float = []
            for cq in col_qty:
                try:
                    col_qty_float.append(float(cq))
                except ValueError:
                    pass
            common_qty = [float(qty) for qty in filtered_quantity if float(qty) in col_qty_float]
            if common_qty:
                matched_qty = common_qty[0]

        # 2. If no match from columns, fallback to first available number (heuristically assuming first number is qty)
        # Note: We safely avoid the destructive removal that was causing qty to be deleted when qty == lst_price
        if matched_qty is None and filtered_quantity:
            # Optionally, remove the matched price if we definitively know what it is
            matched_qty = float(filtered_quantity[0])

        product['quantity'] = matched_qty if matched_qty is not None else 1.0
        return product

    def find_product_tax(self, product, row, invoice_line_column_values):
        """
        Update the product tax based on the extracted row and values.
        :param product: Product information.
        :param row: Extracted row from the table.
        :param invoice_line_column_values: Values extracted from the table data.
        :return: Updated product information.
        """
        # Retrieve relevant tax configurations and tax rates
        invoice_digitization = self.env['invoice.digitization'].search(
            [('active_configuration', '=', True),
             ('account_type', '=', self.move_type)])
        sales_tax = self.env['account.tax'].search(
            [('active', '=', True), ('type_tax_use', '=', 'sale')])
        purchase_tax = self.env['account.tax'].search(
            [('active', '=', True), ('type_tax_use', '=', 'purchase')])
        row = list(row)
        # Extract percentage numbers from the row
        if invoice_digitization.tax_type == 'tax_per_line':
            percentage_numbers = (
                re.findall(r'\d+(?:\.\d+)?%', str(row).strip()))
            if 'tax_ids' in invoice_line_column_values.keys():
                actual_tax = [percentage for percentage in percentage_numbers if
                              percentage in invoice_line_column_values[
                                  'tax_ids']]
            else:
                actual_tax = percentage_numbers
        else:
            actual_tax = invoice_line_column_values['tax_ids'] if (
                    'tax_ids' in invoice_line_column_values.keys()) else []
        # Update the product tax based on the actual tax values
        for tax in actual_tax:
            formatted_tax = float(tax.strip('%'))
            if self.move_type == 'out_invoice':
                for s_tax in sales_tax:
                    if formatted_tax == s_tax.amount:
                        product['tax_ids'] = [s_tax.id]
            elif self.move_type == 'in_invoice':
                for p_tax in purchase_tax:
                    if formatted_tax == p_tax.amount:
                        product['tax_ids'] = [p_tax.id]
        return product

    def find_product_discount(self, product, row, invoice_line_column_values):
        """
        Update the product discount based on the extracted row and values.
        :param product: Product information.
        :param row: Extracted row from the table.
        :param invoice_line_column_values: Values extracted from the table data.
        :return: Updated product information.
        """
        row = list(row)
        # Remove currency symbols from the row
        currency_symbols = set(
            currency.symbol for currency in self.env['res.currency'].search([]))
        row = [value for value in row if not any(
            currency_symbol in str(value).split() for currency_symbol in
            currency_symbols)]
        row = [value for value in str(row).split() if "%" not in value]
        # Find discount matches in the row
        discount_match = re.findall(
            r'\b(\d+(\.\d{1,2})?)(?![%])\b', str(row))
        filtered_discount = []
        for match in discount_match:
            filtered_discount += (
                tuple(item for item in match if
                      item != '' and not item.startswith(
                          '.')))
        for disc in filtered_discount:
            if self.move_type == 'out_invoice':
                if float(disc) == product['lst_price']:
                    filtered_discount.remove(disc)
                    break
            elif self.move_type == 'in_invoice':
                if float(disc) == product['standard_price']:
                    filtered_discount.remove(disc)
                    break
        filtered_discount = [qty for qty in filtered_discount if
                             str(qty) != product['default_code']]
        # Update the product discount based on matches with extracted discounts
        if 'discount' in invoice_line_column_values.keys():
            product_discount = [float(qty) for qty in filtered_discount if
                                qty in invoice_line_column_values['discount']]
        else:
            product_discount = []
        product['discount'] = max(
            product_discount) if product_discount else 0.00
        return product

    def action_create_products(self, combined_table,
                               invoice_line_column_values):
        """
        Create products based on the combined table data.
        :param combined_table: Combined table data.
        :param invoice_line_column_values: Values extracted from the table data.
        :return: List of created products by OCR.
        """
        # Fetch invoice digitization configuration
        invoice_digitization = self.env['invoice.digitization'].search(
            [('active_configuration', '=', True),
             ('account_type', '=', self.move_type)])
        # Check if product creation type is 'create_product'
        if invoice_digitization.product_creation_type == 'create_product':
            if not combined_table.empty:
                # Extract relevant columns based on configured keywords
                columns_to_keep = []
                df = combined_table
                for col in df.columns:
                    values = df[col].tolist()
                    cleaned_values = [str(item).replace(
                        '\n',
                        '') for item in values]
                    keywords = set(
                        keyword.name.lower() for field in
                        invoice_digitization.invoice_line_field_details_ids
                        if field.invoice_line_field_id.name in [
                            'product_id', 'price_unit',
                            'default_code']
                        for keyword in field.line_field_keyword_ids)
                    for val in cleaned_values:
                        if any(keyword in val.lower() for keyword in keywords):
                            columns_to_keep.append(col)
                df_filtered = df[columns_to_keep]
                df_filtered = df_filtered.applymap(
                    lambda x: float('nan') if isinstance(x, str) and x.strip() == '' else x)
            df_filtered = df_filtered.dropna(how='any')
            # Filter and clean rows from combined table data
            date_pattern = r'\d{2}/\d{2}/\d{4}'
            table_rows = []
            for row in df_filtered.itertuples(index=False):
                row = list(set(row))
                row_data = []
                for data in row:
                    row_data.append(data)
                cleaned_row_data = [item.strip() for item in
                                    row_data if item.strip()]
                filtered_row_data = [item for item in cleaned_row_data if
                                     not re.match(date_pattern, item)]
                cleaned_list = [item.replace('\xa0', ' ') for item
                                in filtered_row_data]
                filtered_cleaned_list = [item.replace('\n', ' ') for item
                                         in cleaned_list]
                table_rows.append(filtered_cleaned_list)
            # Extract relevant field names for product details
            field_names_to_check = ['product_id', 'price_unit',
                                    'default_code']
            keywords = set(
                keyword.name.lower() for field in
                invoice_digitization.invoice_line_field_details_ids
                if
                field.invoice_line_field_id.name in field_names_to_check
                for keyword in field.line_field_keyword_ids)
            # Filter rows based on configured keywords
            new_table_rows = [table_rows[table_rows.index(row) + 1:] for row
                              in
                              table_rows if any(
                    keyword in str(row).lower() for keyword in keywords)]
            product_ids = self.env['product.product'].search([])
            if new_table_rows:
                filtered_table_rows = [
                    row for row in new_table_rows[0] if not any(
                        product.name.lower() in str(row).lower() for product
                        in
                        product_ids)]
            else:
                filtered_table_rows = [
                    row for row in table_rows if not any(
                        product.name.lower() in str(row).lower() for product
                        in
                        product_ids)]
            final_table_rows = []
            # Process filtered rows to extract product details
            for row in filtered_table_rows:
                split_row = str(row).split()
                special_char_pattern = r'[^\w.%]+'
                cleaned_split_row = [re.sub(special_char_pattern,
                                            '', item)
                                     for item in split_row]
                price_in_row = [float(num) for num in cleaned_split_row if
                                re.match(r'-?\d+\.\d+', num)]
                if price_in_row:
                    final_table_rows.append(row)
            final_product_details = []
            ocr_products = []
            # extract the product code and name to create the product
            for row in final_table_rows:
                assumed_product_name = []
                product_code = False
                for item in row:
                    for value in invoice_line_column_values['product_id']:
                        if value.lower() in item.lower():
                            column_keys = \
                                [key for key in
                                 invoice_line_column_values.keys()]
                            split_value = value.split()
                            if 'default_code' not in column_keys:
                                for val in split_value:
                                    if val in [split_value[0],
                                               split_value[-1]]:
                                        if (re.match(
                                                r'^[a-zA-Z0-9]+$', val)
                                                and re.search(r'\d', val)):
                                            product_code = val
                                        elif re.match(
                                                r'^[a-zA-Z0-9!@#$%^&*\[\]_]+$',
                                                val) and not val.isalpha():
                                            product_code = val
                                        elif (re.match(
                                                r'^[0-9]+$', val)
                                              and not val.isalpha()):
                                            product_code = val
                                if product_code:
                                    value = value.replace(product_code,
                                                          '')
                                    assumed_product_name.append(value)
                                else:
                                    assumed_product_name.append(value)
                                product_code = [product_code]
                            else:
                                assumed_product_name.append(value)
                                product_code = \
                                    [item for item in row if item in
                                     invoice_line_column_values[
                                         'default_code']]
                    # assign product code
                assumed_product_code = product_code
                # Remove currencies from row
                currency_names = self.env['res.currency'].search_read(
                    [('active', 'in', [False, True])], ['name', 'symbol'])
                for item in row:
                    for currency in currency_names:
                        if currency['name'] in str(row):
                            new_item = item.replace(currency['name'], '')
                            row.remove(item)
                            row.append(new_item)
                numerical_row = [item for item in row if
                                 not any(char.isalpha() for char in item)]
                split_numerical_row = str(numerical_row).split()
                special_char_pattern = r'[^\w.%]+'
                cleaned_split_numerical_row = [
                    re.sub(special_char_pattern, '', item) for
                    item
                    in split_numerical_row]
                price_in_row = [float(num) for num in
                                cleaned_split_numerical_row if
                                re.match(r'-?\d+\.\d+', num)]
                assumed_product_price = max(
                    price_in_row) if price_in_row else 0
                assumed_product_name = [' '.join(item.split()) for item in
                                        assumed_product_name]
                product_details = {'name': assumed_product_name[
                    0], 'ocr_product': True,
                                   'detailed_type': 'product'} if (
                    assumed_product_name) else {'name': None,
                                                'ocr_product': True, }
                if self.move_type == 'out_invoice':
                    product_details[
                        'lst_price'] = assumed_product_price \
                        if assumed_product_price else None
                elif self.move_type == 'in_invoice':
                    product_details[
                        'standard_price'] = assumed_product_price \
                        if assumed_product_price else None
                product_details[
                    'default_code'] = assumed_product_code[
                    0] if assumed_product_code else None
                final_product_details.append(product_details)
            # Create the product by extracting details.
            for details in final_product_details:
                ocr_product = self.env['product.product'].create([details])
                ocr_products.append(ocr_product)
            return ocr_products


    def action_retry_digitization(self):
        """
           Retry the digitization process for the current invoice.

           This method clears the existing invoice line items and re-triggers
           the digitization process by calling `action_send_digitization()`.
       """
        self.invoice_line_ids = None
        self.action_send_digitization()


    def get_details_ai(self, text, pdf_text, file_path):
        """
           Extract invoice details from a given PDF using an AI-powered service.

           This method sends the PDF text to an AI endpoint to extract structured
           invoice data such as:
               - Product codes
               - Quantities
               - Unit prices
               - Tax details
               - Discounts
               - Partner (billing entity) information

           The AI is instructed to validate extracted values by recalculating totals
           and cross-verifying them against the invoice to detect discrepancies.
           If the response is too long or an error occurs, the digitization status
           is updated accordingly.

           Args:
               text (str): Supplementary text extracted from the invoice.
               pdf_text (str): Full text extracted from the uploaded PDF.
               file_path (str): Path to the PDF file.

           Returns:
               str | None: The AI-processed invoice details if successful,
               otherwise None. Updates the record state in case of errors.
       """
        company_name = self.env.company.name
        gpt_response = ""
        try:
            conversation_history = [
                {'role': 'user',
                 'content':
                     f'Please extract detailed invoice information, product '
                     f'specifics, and pricing from a provided PDF file. Your '
                     f'task involves capturing key data such as the '
                     f'product code,quantity, individual item price, '
                     f'tax details, and any available discounts. Its crucial to'
                     f'accurately discern the unit price for each product, not'
                     f'solely the total cost. Be aware that discrepancies may'
                     f'occur in cases where figures like price, quantity, or'
                     f' discounts are misaligned, so exercise caution during'
                     f' extraction.To validate accuracy, calculate the total'
                     f' price of each product considering quantity and '
                     f'discounts applied.Compare this calculated amount with'
                     f' the provided total price to identify any discrepancies'
                     f' and rectify them promptly. Further, sum up the '
                     f'individual product prices to derive the total cost of'
                     f' all items and cross-verify it with the total price'
                     f' stated on the invoice. Any errors found during this'
                     f' process can be rectified by pinpointing the mistake'
                     f' and making the necessary corrections.When identifying'
                     f' the correct partner name for billing purposes, it is'
                     f' essential to consider the individual or company to '
                     f'whom the bill is addressed. Ensure that the context '
                     f'aligns with the billing address provided and avoid '
                     f'using {company_name} in this process.'
                 }]
            config_parameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = config_parameter.get_param(
                'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
            response = iap_tools.iap_jsonrpc(
                olg_api_endpoint + "/api/olg/1/chat", params={
                    'prompt': pdf_text,
                    'conversation_history': conversation_history or [],
                    'version': release.version,
                }, timeout=30)
            if response['status'] == 'success':
                gpt_response += response['content']
                if _("Continued in next message") in response['content']:
                    conversation_history = [{'role': 'user',
                                             'content': text},
                                            {'role': 'assistant',
                                             'content': response['content']}]
                    response = iap_tools.iap_jsonrpc(
                        olg_api_endpoint + "/api/olg/1/chat", params={
                            'prompt': 'continue',
                            'conversation_history': conversation_history or [],
                            'version': release.version,
                        }, timeout=30)
                    if response['status'] == 'success':
                        gpt_response += response['content']
                        return gpt_response
                else:
                    return response['content']
            elif response['status'] == 'error_prompt_too_long':
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"The PDF content you submitted was too long.")})
            else:
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"Data cannot be read, digitization failed.")})
        except Exception as ecx:
            self.ocr_digitize_failed = True
            self.ocr_digitize_completed = False
            self.write({'ocr_digitize_message': _(
                f"The AI Failed to Digitize the Document.")})
            _logger.error(f"AccessError details: {ecx}")


    def get_invoice_details(self, pdf_details):
        """
        Extract invoice metadata from PDF text using an AI service.

        Sends cleaned PDF text to an AI endpoint, which returns a dictionary of
        invoice fields in a strict schema.

        Fields:
            - partner_name, invoice_date, invoice_date_due, delivery_date,
              payment_reference, customer_ref, payment_term,
              incoterm_id, incoterm_location

        Args:
            pdf_details (str): Raw text extracted from the invoice PDF.

        Returns:
            dict | None: Extracted invoice details, or None on failure.

        Notes:
            - Dates are normalized to '%m/%d/%Y'.
            - Missing fields default to an empty string.
            - Response must be a dictionary only (no extra text).
        """
        pdf_details = '\n'.join(
            [line.strip() for line in pdf_details.splitlines() if
             line.strip()])
        try:
            company_name = self.env.company.name
            conversation_history = [
                {'role': 'user',
                 'content': f"Find and extract invoice details, including "
                            f"partner name, invoice date, invoice due date, "
                            f"delivery date, payment reference, "
                            f"customer reference, payment terms, incoterm, and"
                            f" incoterm location represented as a dictionary."
                            f" When extracting the partner name, consider the "
                            f"person or company billed to and do not include "
                            f"{company_name}."
                            f" Ensure correct identification of the payment "
                            f"reference and the customer reference. "
                            f"The dictionary keys should correspond to "
                            f"partner_name, invoice_date, invoice_date_due, "
                            f"delivery_date, payment_reference, customer_ref, "
                            f"payment_term, incoterm_id, and incoterm_location."
                            f" Note that if the dates in the document like "
                            f"this 'Aug 13, 2018', convert them to proper "
                            f"number format like this '%m/%d/%Y'. If the values"
                            f"are null, assign a blank value to the "
                            f"corresponding key.The response should only "
                            f"contain the dictionary without any additional"
                            f" text.(It must strictly follow these guidelines)"
                 }]
            config_parameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = config_parameter.get_param(
                'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
            response = iap_tools.iap_jsonrpc(
                olg_api_endpoint + "/api/olg/1/chat", params={
                    'prompt': pdf_details,
                    'conversation_history': conversation_history or [],
                    'version': release.version,
                }, timeout=30)
            if response['status'] == 'success':
                if isinstance(response['content'], str):
                    try:
                        invoice_details = json.loads(response['content'])
                    except json.JSONDecodeError:
                        start_index = response['content'].find("{")
                        end_index = response['content'].find("}")
                        # Extract the substring containing the list
                        extracted_invoice_details = response['content'][
                            start_index:end_index + 1]
                        invoice_details = json.loads(
                            extracted_invoice_details)
                    return invoice_details
            elif response['status'] == 'error_prompt_too_long':
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"Data cannot be read, digitization failed.")})
            else:
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"Failed to extract the Invoice field details.")})
        except Exception as exc:
            self.ocr_digitize_failed = True
            self.ocr_digitize_completed = False
            self.write({'ocr_digitize_message': _(
                f"The AI Failed to Digitize the Document.")})
            _logger.error(f"AccessError details: {exc}")


    def get_product_details(self, pdf_details):
        """
        Extract product line details from PDF text using an AI service.

        The AI returns a JSON list of product dictionaries with keys:
            - product_name (without code), product_code, quantity, quantity_uom,
              price_unit, product_tax (percentage with % or "false"), and discount (0 if missing).

        Behavior:
            - If `tax_type` is `tax_per_line`, extract tax per product line.
            - Otherwise, apply a single tax to all products.
            - Response must be a valid JSON string (list of dicts with values in quotes).

        Args:
            pdf_details (str): Extracted PDF text.

        Returns:
            list[dict] | None: List of product details or None if extraction fails.
        """
        pdf_details = '\n'.join(
            [line.strip() for line in pdf_details.splitlines() if
             line.strip()])
        invoice_digitization = self.env['invoice.digitization'].search(
            [('active_configuration', '=', True),
             ('account_type', '=', self.move_type)])
        try:
            if invoice_digitization.tax_type == 'tax_per_line':
                conversation_history = [
                    {'role': 'user',
                     'content': f"Find and extract product details from this "
                                f"invoice, including product name, product code"
                                f",quantity, product unit of measure ,"
                                f"product price,product tax in percentage "
                                f"format with % symbol if tax is not applicable "
                                f"to the product make it as false value."
                                f"Add if multiple tax in product line"
                                f"if the discount is empty the assign as 0."
                                f"The dictionary keys should correspond to product_name"
                                f"(product name without product code), "
                                f"product_code, quantity,quantity_uom, "
                                f"price_unit, product_tax, discount.Add the "
                                f"each product details to the list as "
                                f"dictionary.The response should only contain"
                                f"the list of dictionary, the values of keys "
                                f"must be in string(in double quotes), no other"
                                f"text and the product name without product "
                                f"code needs strictly follow.(it must very very"
                                f" strictly follow) and do not return as python"
                                f" just as string(dont add new line command)."
                     }]
            else:
                conversation_history = [
                    {'role': 'user',
                     'content': f"Find and extract product details from this "
                                f"invoice, including product name, product code"
                                f",quantity, product unit of measure ,"
                                f"product price,product tax in percentage "
                                f"format with % symbol and cosider single tax "
                                f"to all the product,discount.The dictionary "
                                f"keys should correspond to product_name"
                                f"(product name without product code), "
                                f"product_code, quantity,quantity_uom, "
                                f"price_unit, product_tax, discount.Add the "
                                f"each product details to the list as "
                                f"dictionary.The response should only contain"
                                f"the list of dictionary, the values of keys "
                                f"must be in string(in double quotes),no other"
                                f"text and the product name without product "
                                f"code needs strictly follow.(it must very very"
                                f"strictly follow) and do not return as python"
                                f"just as string(dont add new line command)."
                     }]
            config_parameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = config_parameter.get_param(
                'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
            response = iap_tools.iap_jsonrpc(
                olg_api_endpoint + "/api/olg/1/chat", params={
                    'prompt': pdf_details,
                    'conversation_history': conversation_history or [],
                    'version': release.version,
                }, timeout=120)
            if response['status'] == 'success':
                if isinstance(response['content'], str):
                    try:
                        response_content = response['content'].replace('\n', '')
                        response_content = response_content.replace(",]", "]")
                        invoice_details = json.loads(response_content)
                    except json.JSONDecodeError:
                        response_content = response['content'].replace('\n', '')
                        response_content = response_content.replace(",]", "]")
                        start_index = response_content.find("[")
                        end_index = response_content.find("]")
                        # Extract the substring containing the list
                        extracted_invoice_details = response_content[
                            start_index:end_index + 1]()
                        invoice_details = json.loads(
                            extracted_invoice_details)
                    return invoice_details
            elif response['status'] == 'error_prompt_too_long':
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"Data cannot be read, digitization failed.")})
            else:
                self.ocr_digitize_failed = True
                self.ocr_digitize_completed = False
                self.write({'ocr_digitize_message': _(
                    f"Failed to extract the Product details.")})
        except Exception as exc:
            self.write({'ocr_digitize_message': _(
                f"The AI Failed to Digitize the Document.")})
            _logger.error(f"AccessError details: {exc}")


    def find_partner_ai(self, text, invoice_details):
        """
        Find a partner based on the extracted text from pdf and create a
        partner if not exist.
        :param text: Extracted text to search for partner information.
        :param invoice_details: Dictionary containing details extracted from the
        pdf using AI Functionality."""
        if not invoice_details:
            return
        partner_ids = self.env['res.partner'].search(
            [('name', '!=', self.env.company.name)])
        partner_name = (invoice_details.get('partner_name') or '').strip()
        if partner_name:
            partner = partner_ids.filtered(
                lambda p: p.name and p.name.lower() == partner_name.lower())
            if partner:
                self.write({'partner_id': partner[0].id})
            else:
                partner_id = self.env['res.partner'].create({
                    'name': partner_name,
                })
                self.write({'partner_id': partner_id.id})
        else:
            normalized_text = ' '.join(text.split())
            found_partners = partner_ids.filtered(
                lambda partner: partner.name and
                re.search(rf'\b{re.escape(partner.name)}\b', normalized_text,
                          re.I))
            if found_partners:
                self.write({'partner_id': found_partners[0].id})


    def get_invoice_date_ai(self, text, invoice_details):
        """
        Extract and set invoice-related dates from the provided text and
        invoice details.
        :param text: Extracted text containing date information.
        :param invoice_details: Dictionary containing details extracted from the
        invoice."""
        # Define regular expressions for date patterns
        dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', text)
        valid_dates = []
        # Format and filter valid dates
        for date in dates:
            try:
                formatted_date = datetime.strptime(
                    date,
                    '%d/%m/%Y').strftime('%m/%d/%Y')
                valid_dates.append(formatted_date)
            except ValueError:
                valid_dates.append(date)
        if invoice_details['invoice_date']:
            invoice_date = datetime.strptime(
                invoice_details['invoice_date'],
                "%m/%d/%Y")
            self.write({'invoice_date': invoice_date})
        else:
            if len(valid_dates) == 1:
                dates = datetime.strptime(
                    valid_dates[0],
                    "%m/%d/%Y")
                self.write({'invoice_date': dates})
            elif len(valid_dates) == 2:
                date_objects = [datetime.strptime(
                    date,
                    '%m/%d/%Y')
                    for date in valid_dates]
                sorted_dates = sorted(date_objects)
                self.write({'invoice_date': sorted_dates[0]})
        if invoice_details['invoice_date_due']:
            invoice_date_due = datetime.strptime(
                invoice_details['invoice_date_due'],
                "%m/%d/%Y")
            self.write({'invoice_date_due': invoice_date_due})
        else:
            if len(valid_dates) == 2:
                date_objects = [datetime.strptime(
                    date,
                    '%m/%d/%Y')
                    for date in valid_dates]
                sorted_dates = sorted(date_objects)
                self.write({'invoice_date_due': sorted_dates[1]})
        if invoice_details['delivery_date']:
            if self.move_type == 'out_invoice':
                delivery_date = datetime.strptime(
                    invoice_details['delivery_date'],
                    "%m/%d/%Y")
                self.write({'delivery_date': delivery_date})


    def action_find_field_values_ai(self, invoice_details, text):
        """
        Update invoice fields using AI-extracted metadata.

        This method maps values from `invoice_details` or fallback text
        search to corresponding Odoo fields.

        Fields updated:
            - payment_reference → payment_reference
            - customer_ref → ref
            - payment_term → invoice_payment_term_id (matched by name or text)
            - incoterm_id → invoice_incoterm_id (matched by code or text)

        Args:
            invoice_details (dict): Extracted invoice metadata from AI.
            text (str): Full invoice text for fallback lookups.
        """
        # Update payment reference if available
        if invoice_details.get('payment_reference'):
            self.write(
                {'payment_reference': invoice_details['payment_reference']})
        # Update customer reference if available
        if invoice_details.get('customer_ref'):
            self.write({'ref': invoice_details['customer_ref']})
        # Update payment term if available
        if invoice_details.get('payment_term'):
            payment_terms = self.env['account.payment.term'].search([])
            found_term = payment_terms.filtered(
                lambda term: term.name.lower() == invoice_details[
                    'payment_term'].lower())
            if not found_term:
                found_term = payment_terms.filtered(
                    lambda term: term.name.lower() in text.lower())
            if found_term:
                self.write({'invoice_payment_term_id': found_term[0].id})
        # Update Incoterm if available
        if invoice_details.get('incoterm_id'):
            incoterms = self.env['account.incoterms'].search(
                [('code', '=', invoice_details['incoterm_id'])])
            if not incoterms:
                incoterms = self.env['account.incoterms'].search([])
                found_incoterms = incoterms.filtered(
                    lambda term: term.code in text)
                if found_incoterms:
                    self.write({'invoice_incoterm_id': found_incoterms[0].id})
            else:
                self.write({'invoice_incoterm_id': incoterms[0].id})


    def action_find_product(self, product_details):
        """
        Update invoice fields using AI-extracted metadata.

        This method maps values from `invoice_details` or fallback text
        search to corresponding Odoo fields.

        Fields updated:
            - payment_reference → payment_reference
            - customer_ref → ref
            - payment_term → invoice_payment_term_id (matched by name or text)
            - incoterm_id → invoice_incoterm_id (matched by code or text)

        Args:
            invoice_details (dict): Extracted invoice metadata from AI.
            text (str): Full invoice text for fallback lookups.
        """
        products = self.env['product.product'].search([])
        for rec in product_details:
            invoice_details = {
                'product_id': None,
                'quantity': 1,
            }
            products_by_code = [product for product in products if
                                product.default_code if
                                product.default_code.lower() == str(
                                    rec['product_code']).lower()] if rec[
                'product_code'] else []
            products_by_name = [
                product for product in products if
                rec['product_name'].lower() == product.name.lower()] \
                if not products_by_code and rec['product_name'] else []
            products_by_display_name = [
                product for product in products
                if rec['product_name'].lower() in product.display_name.lower()
            ] if len(products_by_name) > 1 else []
            if products_by_code:
                invoice_details['product_id'] = products_by_code[0].id
            elif products_by_display_name:
                invoice_details['product_id'] = products_by_display_name[0].id
            elif products_by_name:
                invoice_details['product_id'] = products_by_name[0].id

            # Extracting quantity from the product details
            qty_match = re.search(r'\d+(\.\d+)?', str(rec['quantity'])) \
                if rec['quantity'] else None
            if qty_match:
                extracted_quantity = qty_match.group(0)
                invoice_details['quantity'] = float(extracted_quantity)

            # Extracting unit of measure from the product details if available
            uom_list = self.env['uom.uom'].search([])
            found_uom = [uom for uom in uom_list if
                         uom.name == rec['quantity_uom']] if (
                    rec['quantity_uom'] and uom_list) else []
            if found_uom:
                invoice_details['product_uom_id'] = found_uom[0].id
            # Extracting product price from the product details
            price_unit = str(rec['price_unit']).replace(',',
                                                        '')  # Remove commas
            price_match = re.search(r'\d+(\.\d+)?', price_unit) if \
                rec['price_unit'] else None
            if price_match:
                extracted_price = price_match.group(0)
                invoice_details['price_unit'] = float(extracted_price)
            # Extracting product tax from the product details
            if self.move_type == 'out_invoice':
                tax_list = self.env['account.tax'].search(
                    [('active', '=', True), ('type_tax_use', '=', 'sale')])
            else:
                tax_list = self.env['account.tax'].search(
                    [('active', '=', True), ('type_tax_use', '=', 'purchase')])
            tax_rate = re.findall(r'\d+%', rec['product_tax'])
            tax_rate = [int(rate.strip('%')) for rate in tax_rate] \
                if rec['product_tax'] != 'false' else 0.0
            product_tax = [tax for tax in tax_list if
                           tax.amount in [float(rate) for rate in
                                          tax_rate]] if tax_list else []
            invoice_details['tax_ids'] = [tax.id for tax in
                                          product_tax] if product_tax else None

            # Extracting product discount from the product details
            discount = re.search(r'\d+(\.\d+)?',
                                 str(rec['discount'])) if rec[
                'discount'] else None
            product_discount = discount.group(0) if discount else None
            invoice_details['discount'] = float(
                product_discount) if product_discount else 0.0
            if invoice_details['product_id']:
                invoice_details['move_id'] = self.id
                self.invoice_line_ids.create(invoice_details)
            else:
                invoice_details['move_id'] = self.id
                self.action_create_product_ai(rec, invoice_details)
            if self.invoice_line_ids:
                self.ocr_digitize_completed = True
                if self.ocr_digitize_completed:
                    self.ocr_digitize_failed = False if (
                        self.ocr_digitize_failed) else False


    def action_create_product_ai(self, product_details, invoice_details):
        """
        Creates a product based on the provided product and invoice details.
        :param product_details: Dictionary containing details of the product
         to be created.
        :param invoice_details: Dictionary containing details of the invoice.
        """
        invoice_digitization = self.env['invoice.digitization'].search(
            [('active_configuration', '=', True),
             ('account_type', '=', self.move_type)])
        if invoice_digitization.product_creation_type == 'create_product':
            if product_details['product_name']:
                product_values = {
                    'name': product_details['product_name'],
                    'default_code': product_details['product_code'],
                    'ocr_product': True,
                    'detailed_type': 'product'
                }
                price_unit = invoice_details.get('price_unit', None)
                if self.move_type == 'out_invoice' and price_unit is not None:
                    product_values['lst_price'] = invoice_details['price_unit']
                if self.move_type != 'out_invoice' and price_unit is not None:
                    product_values['standard_price'] = invoice_details[
                        'price_unit']
                uom_unit = invoice_details.get('product_uom_id', None)
                if uom_unit is not None:
                    product_values['uom_id'] = invoice_details['product_uom_id']
                    product_values['uom_po_id'] = invoice_details[
                        'product_uom_id']
                product_id = self.env['product.product'].create(product_values)
                invoice_details['product_id'] = product_id.id
                self.invoice_line_ids.create(invoice_details)
