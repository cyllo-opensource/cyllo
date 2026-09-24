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
import os
import re
import tempfile

# imports of odoo
from odoo import _, api, fields, models, release
from odoo.addons.iap.tools import iap_tools

# Import of unknown third party lib
_logger = logging.getLogger(__name__)

DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'
GPT_MODEL = "gpt-3.5-turbo"

try:
	import camelot
	import fitz
	import pandas as pd
except ImportError as e:
	package_name = str(e).split(' ')[-1]
	_logger.debug('Cannot import the required external dependency: %s',
	              package_name)

try:
	from openai import OpenAI as _OpenAI, AuthenticationError as _AuthError
except ImportError:
	_OpenAI = None
	_AuthError = None

try:
	import pdfplumber
except ImportError:
	pdfplumber = None


class PurchaseOrder(models.Model):
	"""
		Extends the 'purchase.order' model to include fields and methods for
		OCR digitization of PDF documents.
		"""
	_inherit = 'purchase.order'

	ocr_digitize_enabled = fields.Boolean(
		string="OCR Enabled",
		compute='_compute_ocr_digitize_enabled')
	message_main_attachment_id = fields.Many2one(
		string="Main Attachment",
		comodel_name='ir.attachment',
		copy=False)
	ocr_digitize_completed = fields.Boolean(string="OCR success status")
	ocr_digitize_failed = fields.Boolean(string="OCR failed status")
	ocr_digitize_message = fields.Char(
		string="OCR Status",
		readonly=True)

	@api.depends('message_main_attachment_id')
	def _compute_ocr_digitize_enabled(self):
		"""
		Compute the OCR digitization status for each record.

		The OCR digitization status is determined based on the configuration
		parameters and the automation type specified in the associated
		purchase digitization settings.
		"""
		for rec in self:
			# Check if OCR digitization is enabled in the system
			is_purchase_ocr_digitization = self.env[
				'ir.module.module'].sudo().search(
				[('name', '=', 'cyllo_purchase_digitization'),
				 ('state', '=', 'installed')])
			if is_purchase_ocr_digitization:
				# Retrieve the relevant purchase digitization settings
				purchase_digitization = self.env[
					'purchase.digitization'].search(
					[('active_configuration', '=', True)])
				# Determine OCR digitization status based on automation type
				if purchase_digitization.automation_type == 'request_digitize':
					rec.write({'ocr_digitize_enabled': True})
				else:
					rec.write({'ocr_digitize_enabled': False})
				# Trigger automatic digitization if configured for auto_digitize
				if (purchase_digitization.automation_type == 'auto_digitize'
					and rec.ocr_digitize_completed != True):
					if rec.state == 'draft' and rec.message_main_attachment_id:
						rec.action_send_digitization()
			else:
				rec.write({'ocr_digitize_enabled': False})

	def action_send_digitization(self):
		"""
		 Perform OCR digitization on a PDF document attached to the record.
		 This method reads the attached PDF document, extracts text content, and
		 processes it to digitize relevant information, such as partner name,
		 purchase fields, and purchase order line details.
		 :raises: Exception if an error occurs during digitization.
		 """
		# Getting the file path from ir.attachments
		file_attachment = self.message_main_attachment_id
		# Check if the file is a PDF
		if file_attachment:
			split_tup = os.path.splitext(file_attachment.name)
			file_path = file_attachment._full_path(file_attachment.store_fname)
			pdf_extension = {'.pdf'}
			if split_tup[1] in pdf_extension:
				# Reading files in the format .pdf
				with open(file_path, mode='rb') as f:
					pdf_data = f.read()
				text = " "
			else:
				# Notify if the document is not a PDF
				self.ocr_digitize_failed = True
				self.ocr_digitize_completed = False
				self.write({
					'ocr_digitize_message':
						'Digitization now works only on PDF documents'})
				return
			try:
				# Extract text using OCR
				doc = fitz.open(file_path)  # open a document
				for page in doc:  # iterate the document pages
					text += page.get_text(flags=8)
				text = '\n'.join(
					[line.strip() for line in text.splitlines() if
					 line.strip()])
				purchase_digitization = self.env[
					'purchase.digitization'].search(
					[('active_configuration', '=', True)])
				if (purchase_digitization.automation_method ==
					'manual_digitization'):
					if pdf_data:
						with tempfile.NamedTemporaryFile(
							suffix='.pdf', delete=False) as temp_pdf_file:
							temp_pdf_file.write(pdf_data)
						# Primary: camelot (lattice then stream)
						tables_dfs = []
						table_data = []
						combined_table = pd.DataFrame()
						try:
							tables = camelot.read_pdf(
								temp_pdf_file.name, pages='all', flavor='lattice')
							if not tables:
								tables = camelot.read_pdf(
									temp_pdf_file.name, flavor='stream', pages='all')
							if tables:
								if len(tables) > 1:
									combined_table = pd.concat(
										[table.df for table in tables],
										ignore_index=True)
								else:
									combined_table = tables[0].df
								for table in tables:
									table_rows = []
									for row in table.df.itertuples(index=False):
										row_data = [
											item.replace('\xa0', ' ').strip()
											for item in row if item.strip()]
										table_rows.append(row_data)
									table_data.append(table_rows)
								tables_dfs = [table.df for table in tables]
						except Exception:
							pass
						# Fallback: pdfplumber when camelot finds nothing
						if not table_data:
							try:
								with pdfplumber.open(temp_pdf_file.name) as pdf_doc:
									for page in pdf_doc.pages:
										tbls = page.extract_tables()
										if not tbls:
											tbls = page.extract_tables(
												table_settings={
													'vertical_strategy': 'text',
													'horizontal_strategy': 'text',
												})
										if not tbls:
											words = page.extract_words()
											if words:
												rows_by_y = {}
												for w in words:
													y_key = round(w['top'] / 5) * 5
													rows_by_y.setdefault(y_key, []).append(w['text'])
												if rows_by_y:
													word_rows = [v for _, v in sorted(rows_by_y.items())]
													max_len = max(len(r) for r in word_rows)
													padded = [r + [''] * (max_len - len(r)) for r in word_rows]
													tbls = [padded]
										for tbl in tbls:
											tables_dfs.append(pd.DataFrame(tbl).fillna('').astype(str))
								if len(tables_dfs) > 1:
									combined_table = pd.concat(tables_dfs, ignore_index=True)
								elif len(tables_dfs) == 1:
									combined_table = tables_dfs[0]
								for df in tables_dfs:
									table_rows = []
									for row in df.itertuples(index=False):
										row_data = [
											str(item).replace('\xa0', ' ').strip()
											for item in row if str(item).strip()]
										table_rows.append(row_data)
									table_data.append(table_rows)
							except Exception:
								pass
						# Perform further actions based on extracted data
						self.find_partner(text)
						self.action_find_field_values(text)
						# Primary: parse lines straight from the PDF text table
						# (reliable, creates missing products, camelot-independent)
						parsed = self._extract_lines_from_pdf_text(file_path)
						if parsed:
							self._create_po_lines_from_parsed(parsed)
						else:
							# Fallback: keyword/column table approach using robust extraction methods
							purchase_line_column_values = \
								self.action_get_purchase_line_columns(
									combined_table, text)
							ocr_products = self.action_create_products(
								combined_table, purchase_line_column_values)
							self.get_order_line(table_data,
							                    purchase_line_column_values)
							if not self.order_line and table_data:
								self._extract_products_from_table(
									table_data, purchase_line_column_values)
							if not self.order_line:
								self._extract_products_from_text(text)
							if self.ocr_digitize_failed:
								for product in (ocr_products or []):
									product.id.unlink()
				else:
					pdf_details = self.get_details_ai(text) if text else None
					quotation_details = self.get_quotation_details(
						pdf_details) if pdf_details else None
					product_details = self.get_product_details(
						pdf_details) if pdf_details else None
					# Perform further actions based on extracted data
					self.find_partner_ai(text, quotation_details)
					self.action_find_field_values_ai(text, quotation_details)
					self.action_find_product(product_details)
				# except Exception:
			except Exception as exc:
				# Handle exceptions during digitization
				self.ocr_digitize_failed = True
				self.ocr_digitize_completed = False
				logging.error(f"Error while processing segment: {exc}")
				self.write({'ocr_digitize_message': _(
					f"Data cannot be read, digitization failed")})
				if self.ocr_digitize_failed:
					return {
						'name': 'AI Digitization',
						'type': 'ir.actions.act_window',
						'res_model': 'digitization.ai.wizard',
						'view_mode': 'form',
						'target': 'new',
						'context': {'default_active_id': self.id},
					}
		else:
			# Notify if no attachments are found
			self.ocr_digitize_failed = True
			self.ocr_digitize_completed = False
			self.write({
				'ocr_digitize_message': _(f"No Attachments To Digitize")})

	def find_partner(self, text):
		"""
		Find a partner based on the extracted text using 'spacy'
		and configured keywords.
		:param text: Extracted text to search for partner information.
		"""
		purchase_digitization = self.env['purchase.digitization'].search(
			[('active_configuration', '=', True)])
		# Get keywords related to the 'partner_id' field
		partner_field_keywords = \
			[keyword.name for field in
			 purchase_digitization.purchase_field_details_ids
			 for keyword in field.field_keyword_ids if
			 field.purchase_field_id.name == 'partner_id']
		# Search for existing partners
		company_partner_id = self.env.company.partner_id
		users = self.env['res.users'].search([('share', '=', False)]).mapped(
			'partner_id')
		if company_partner_id:
			partner_ids = self.env['res.partner'].search(
				[('id', '!=', company_partner_id.id),
				 ('id', 'not in', users.ids)]) if users else self.env[
				'res.partner'].search(
				[('id', '!=', company_partner_id.id)])
		else:
			partner_ids = self.env['res.partner'].search(
				[('id', 'not in', users.ids)]) if users else self.env[
				'res.partner'].search([])
		# Primary: the non-company address block, matched by name and VAT.
		block = self._detect_counterparty_block(text, self.env.company)
		if block:
			partner = self._match_partner_from_block(partner_ids, block)
			if not partner:
				values = {'name': block['name'], 'is_company': True}
				if block['vat']:
					values['vat'] = block['vat']
				if block['street']:
					values['street'] = block['street']
				partner = self.env['res.partner'].create(values)
			self.partner_id = partner.id
			return
		keyword_match = [
			re.search(rf'({re.escape(keyword.lower())})', text.lower())
			for keyword in
			partner_field_keywords] if partner_field_keywords else []
		first_match = next((m for m in keyword_match if m), None)
		text_window = text[
			first_match.start():first_match.start() + 45] if first_match else ''
		normalized_window = ' '.join(text_window.split())
		found_partners = partner_ids.filtered(
			lambda partner: partner.name
			and re.search(rf'\b{re.escape(partner.name)}\b',
			              normalized_window, re.I))
		if found_partners:
			found_partners = found_partners.sorted(
				key=lambda partner: len(partner.name or ''), reverse=True)
			self.write({'partner_id': found_partners[0].id})
		# If no partner is found in the window, search in the entire text
		normalized_text = ' '.join(text.split())
		found_partners_text = partner_ids.filtered(
			lambda partner: partner.name
			and re.search(rf'\b{re.escape(partner.name)}\b',
			              normalized_text, re.I)) if not found_partners else partner_ids.browse()
		if found_partners_text:
			found_partners_text = found_partners_text.sorted(
				key=lambda partner: len(partner.name or ''), reverse=True)
			self.write({'partner_id': found_partners_text[0].id})
		if not found_partners and not found_partners_text:
			partner_details = self.get_partner_details_ai(text)
			if partner_details:
				partner_name = partner_details.get('partner_name')
				street = partner_details.get('street')
				city = partner_details.get('city')
				state_name = partner_details.get('state')
				state = self.env['res.country.state'].search(
					[('name', '=', state_name)])
				new_found_partner = self.env['res.partner'].create({
					'name': partner_name
				}) if partner_name else None
				if new_found_partner:
					new_found_partner.write({
						'street': street,
						'city': city,
					})
				if state:
					new_found_partner.write({'state_id': state})
				self.write(
					{'partner_id': new_found_partner.id}) if (
					new_found_partner) else None

	def get_partner_details_ai(self, text):
		"""
		Retrieve partner details from an AI service based on the provided text.
			Args:
				text (str): The text to be analyzed for partner details.
			Returns:
				dict: A dictionary containing partner details such as name,
				street, city, state, and country.If values are null,
				corresponding keys are assigned blank values.The response
				strictly follows the specified guidelines and does not contain
				any additional text.If extraction fails, returns an empty
				 dictionary.
			"""
		try:
			company_name = self.env.company.name
			conversation_history = [
				{'role': 'user',
				 'content': f"Find partner details from this purchase "
				            f"quoatation like customer name and address of the"
				            f" customer. When extracting the customer name,"
				            f" consider the person billed to and do not"
				            f" include {company_name}.The dictionary keys"
				            f" should correspond to partner_name,street, city,"
				            f" state, country.If the values are null,"
				            f" assign a blank value to the corresponding key."
				            f"The response should only contain the dictionary "
				            f"without any additional text and do not add new"
				            f" line command and unwanted spaces."
				            f"(It must strictly follow these guidelines)"}]
			content = self._make_ai_request(text, conversation_history)
			if content and isinstance(content, str):
				try:
					partner_details = json.loads(content)
				except json.JSONDecodeError:
					start_index = content.find("{")
					end_index = content.find("}")
					extracted_purchase_details = content[
						start_index:end_index + 1]
					partner_details = json.loads(extracted_purchase_details)
				return partner_details
			self.ocr_digitize_failed = True
			self.ocr_digitize_completed = False
			self.write({'ocr_digitize_message': _(
				"Failed to Identify the Customer.")})
		except Exception as exc:
			self.ocr_digitize_failed = True
			self.ocr_digitize_completed = False
			self.write({'ocr_digitize_message': _(
				"Failed to Identify the Customer.")})
			logging.error(f"AccessError details: {exc}")

	def action_find_field_values(self, text):
		"""
		Find and update field values in the invoice based on the provided text.
		:param text: Text content to extract field values from.
		"""
		# Retrieve invoice digitization settings
		purchase_digitization = self.env['purchase.digitization'].search(
			[('active_configuration', '=', True)])
		if purchase_digitization.purchase_field_details_ids:
			for field in purchase_digitization.purchase_field_details_ids:
				for keyword in field.field_keyword_ids:
					keyword_pattern = rf'({re.escape(keyword.name.lower())})'
					keyword_match = re.search(keyword_pattern, text.lower())
					# find the text area of the provided keyword
					if keyword_match:
						# Get the start position of the match
						keyword_start = keyword_match.start()
						window_size = 47
						text_window = text[
							keyword_start:keyword_start + window_size]
						if field.purchase_field_id.ttype == 'char':
							char_text_window = text[
								keyword_start:keyword_start + 40]
							keyword_split = keyword.name.split()
							if len(keyword_split) > 1:
								keyword_pattern = \
									rf'({re.escape(keyword_split[-1].lower())})'
								keyword_split_match \
									= re.search(keyword_pattern,
									            char_text_window.lower())
								keyword_split_start = \
									keyword_split_match.start()
								char_text_window \
									= char_text_window[keyword_split_start:
									                   keyword_split_start + 40]
							# Split the text window into words
							split_char_text_window = char_text_window.split()
							if len(split_char_text_window) > 1:
								# Extract the desired word after the keyword
								extracted_word = split_char_text_window[1]
								self.write({
									field.purchase_field_id.name: extracted_word
								})
						elif field.purchase_field_id.ttype == 'many2one':
							model_name = field.purchase_field_id.relation
							records = self.env[model_name].search([])
							found_records = [rec for rec in records
							                 if rec.name.lower() in
							                 text_window.lower() or
							                 rec.name in text.lower()]
							if found_records:
								self.write({field.purchase_field_id.name
											: found_records[0].id})
							if field.purchase_field_id.name == 'incoterm_id':
								incoterm_records = [
									rec for rec in records if
									rec.code in text_window or rec.code in text]
								if incoterm_records:
									self.write({field.purchase_field_id.name
												: incoterm_records[0].id})

	def action_get_purchase_line_columns(self, combined_table, text):
		"""
		Extracts relevant details from a combined table based on configured
		keywords for purchase digitization.
		Note:
			This method relies on configured keywords and field mappings for
			extracting details such as quantity, tax, discount, and price unit
			from the given combined_table and associated text.

			The extracted values are returned in a dictionary format for further
			processing in the purchase digitization workflow.
		"""
		purchase_digitization = self.env['purchase.digitization'].search(
			[('active_configuration', '=', True)])
		purchase_line_values = {}
		if not combined_table.empty:
			for col in combined_table.columns:
				if purchase_digitization.purchase_line_field_details_ids:
					for field in purchase_digitization.purchase_line_field_details_ids:
						for keyword in field.line_field_keyword_ids:
							column_values = combined_table[col].tolist()
							column_values = [str(item).replace('\n', ' ') for
							                 item
							                 in
							                 column_values]
							column_values = [str(item).replace('\xa0', ' ') for
							                 item
							                 in
							                 column_values]
							if any(keyword.name.lower() in str(val).lower() for
							       val
							       in column_values):
								cleaned_column_values = [item for item in
								                         column_values
								                         if item.strip() != '']
								for val in cleaned_column_values:
									if keyword.name.lower() in val.lower():
										keyword_index = \
											cleaned_column_values.index(val)
										values_after_keyword \
											= cleaned_column_values[
											keyword_index + 1:]
										if (field.purchase_line_field_id.name
											== 'product_qty'):
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
														for vals in split_value:
															if unit.name.lower() == vals.lower():
																split_value.remove(
																	vals)
																values_after_keyword.remove(
																	value)
																values_after_keyword.append(
																	split_value[
																		0])
															if (currency.symbol
																== vals):
																values_after_keyword.remove(
																	value)
											extracted_numbers = []
											for item in values_after_keyword:
												# Use regular expression
												# to find numeric values
												numeric_values = re.findall(
													r'\b\d+\.*\d*\b(?!\%)',
													item)
												for value in numeric_values:
													# Check if the numeric value
													# is not associated with a
													# string
													if not any(
														char.isalpha()
														for char in
														item):
														(extracted_numbers.
														 append(value))
											values_after_keyword = list(
												set(extracted_numbers))
										elif (field.purchase_line_field_id.name
										      == 'taxes_id'):
											if (purchase_digitization.tax_type
												== 'tax_per_line'):
												split_tax_column = [
													val for value in
													values_after_keyword for val
													in value.split()]
												percentage_numbers = (
													re.findall(
														r'\d+(?:\.\d+)?%',
														str(split_tax_column)))
												values_after_keyword = \
													percentage_numbers
										elif (field.purchase_line_field_id.name
										      == 'discount'):
											split_values = [
												item.split() for item in
												values_after_keyword]
											flattened_list = [item for sublist
											                  in split_values
											                  for
											                  item in sublist]
											filtered_list = [disc for disc in
											                 flattened_list if
											                 '%' not in disc]
											values_after_keyword = filtered_list
										elif (field.purchase_line_field_id.name
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
											split_values_after_keyword = [
												val
												for value
												in
												filtered_values_after_keyword
												for val in value.split()
												if
												not re.search(
													r'\d+%',
													val)]
											price_pattern = \
												r'(\d+(\.\d{1,2})?)(?![\d%]*%)'
											prices = []
											for vals in \
												split_values_after_keyword:
												price_match = re.match(
													price_pattern, val)
												if price_match:
													price = float(
														price_match.group())
													prices.append(price)
												else:
													if not any(
														char.isalpha() for
														char in vals):
														val = ''.join(
															char for char in
															vals
															if
															char.isdigit() or
															char == '.')
														prices.append(val)
											prices = [item for item in prices if
											          item != '']
											values_after_keyword = prices
								if values_after_keyword:
									purchase_line_values[
										field.purchase_line_field_id.name] = \
										values_after_keyword
								else:
									purchase_line_values[
										field.purchase_line_field_id.name] = \
										cleaned_column_values
								break  # Stop searching once the column is found
							if (purchase_digitization.tax_type ==
								'tax_per_invoice'):
								if (field.purchase_line_field_id.name ==
									'taxes_id'):
									for line_keyword in (
										field.line_field_keyword_ids):
										keyword_pattern = rf'\
                                        ({re.escape(line_keyword.name.lower())})'
										keyword_match = re.search(
											keyword_pattern,
											text.lower())
										if keyword_match:
											# Get the start position
											# of the match
											keyword_start = keyword_match.start()
											window_size = 45
											text_window = \
												text[keyword_start:
												     keyword_start +
												     window_size]
											percentage_numbers = (
												re.findall(
													r'\d+(?:\.\d+)?%',
													str(text_window)))
											if not percentage_numbers:
												percentage_numbers = re.findall(
													r'\d+(?:\.\d+)?%',
													text)
											values_after_keyword = \
												percentage_numbers
											purchase_line_values[
												field.purchase_line_field_id.
												name] = values_after_keyword
		return purchase_line_values

	def get_order_line(self, table_data, purchase_line_column_values):
		"""
		Create order lines based on extracted table data.
		:param table_data: Structured table data extracted from the PDF.
		:param purchase_line_column_values: Values extracted from the data.
		"""
		product_ids = self.env['product.product'].search_read(
			[], ['name', 'default_code', 'lst_price', 'display_name',
			     'standard_price'])
		for product in product_ids:
			product['taxes_id'] = None
		# Find products in the table data based on name, code, or display name
		found_products_with_display_name = [product for data in table_data for
		                                    row in
		                                    data for product in product_ids if
		                                    product['display_name'] in str(row)]

		cleaned_table_data = [
			[[item.replace('\n', '') for item in row] for row in data] for data
			in table_data]
		table_data_copy = cleaned_table_data.copy()
		new_table_data = [[row for row in data if all(
			product['display_name'] not in str(row) for product in product_ids)]
		                  for data in table_data_copy]
		found_products_with_name = [product for data in new_table_data for row
		                            in
		                            data for product in product_ids if
		                            product['name'] in str(row)]
		found_products_with_all_name = (
			found_products_with_display_name +
			[item for item in found_products_with_name if item['id'] not in
			 {value['id'] for value in found_products_with_display_name}])
		found_display_name_rows = [row for data in cleaned_table_data for row in
		                           data
		                           for
		                           product in
		                           product_ids if
		                           product['display_name'] in str(row)]
		found_name_rows = [row for data in cleaned_table_data for row in data
		                   for
		                   product in
		                   product_ids if product['name'] in str(row)]
		found_all_name_rows = [list(sublist) for sublist in
		                       set(tuple(sublist) for sublist in
		                           found_display_name_rows + found_name_rows)]
		found_products_with_code = [product for data in cleaned_table_data for
		                            row in
		                            data for product in product_ids if
		                            str(product['default_code']) in str(row)]
		found_code_rows = [row for data in cleaned_table_data for row in data
		                   for
		                   product in
		                   product_ids if
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
		# Remove rows in found_name_rows that are also in found_code_rows
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
		final_purchase_lines = []
		# Create final invoice lines based on found products and rows
		if actual_products:
			for product in actual_products:
				for row in actual_rows:
					if (str(product['default_code']) in str(row) or product[
						'display_name'].replace(',', '') in str(row) or
						str(row) in product['display_name']):
						final_product_price = self.find_product_price(
							product, row, purchase_line_column_values)
						final_product_qty = self.find_product_quantity(
							product, row, purchase_line_column_values)
						final_product_tax = self.find_product_tax(
							product, row, purchase_line_column_values)
						final_product_discount = self.find_product_discount(
							product, row, purchase_line_column_values)
				purchase_line = {'order_id': self.id,
				                 'product_id': product['id'],
				                 'product_qty': final_product_qty[
									 'product_qty'] if final_product_qty[
									 'product_qty'] else 1,
				                 'price_unit': final_product_price[
									 'price_unit'],
				                 'taxes_id': final_product_tax['taxes_id'] if
								 final_product_tax['taxes_id'] else None,
				                 'discount': final_product_discount['discount']}
				final_purchase_lines.append(purchase_line)
			if final_purchase_lines:
				for purchase_line in final_purchase_lines:
					self.order_line.create(purchase_line)
					self.ocr_digitize_completed = True
				if self.ocr_digitize_completed:
					self.ocr_digitize_failed = False if (
						self.ocr_digitize_failed) else False
		else:
			self.ocr_digitize_failed = True
			self.ocr_digitize_completed = False
			self.write({
				'ocr_digitize_message': _(
					f"Data cannot be read, digitization failed.")})

	def find_product_price(self, product, row, purchase_line_column_values):
		"""
		Update the product price based on the extracted row from the uploaded PO.
		:param product: Product information (dictionary).
		:param row: Extracted row from the table.
		:param purchase_line_column_values: Column values from the PO.
		:return: Updated product dictionary with 'price_unit'.
		"""
		row = list(row)
		# Remove currency symbols
		currency_symbols = set(
			currency.symbol for currency in self.env['res.currency'].search([])
		)
		row = [value for value in row if not any(
			currency_symbol in str(value) for currency_symbol in
			currency_symbols)]
		# Remove percentages and split row
		row = [value for value in str(row).split() if "%" not in value]

		# Extract numeric values
		price_matches = re.findall(r'\b(\d+(\.\d{1,2})?)\b', str(row))
		filtered_prices = []
		for match in price_matches:
			filtered_prices += (
				tuple(item for item in match if
				      item != '' and not item.startswith('.'))
			)

		# Remove irrelevant numbers (product code etc.)
		filtered_prices = [p for p in filtered_prices if
		                   str(p) != str(product.get('default_code', ''))]

		# Decide price based on cost price
		if product.get('standard_price', 0) == 0:
			# If no cost price → take from PO (2nd value preferred)
			if len(filtered_prices) > 1:
				product['price_unit'] = float(filtered_prices[1])
			# elif filtered_prices:
			#     product['price_unit'] = float(filtered_prices[0])
			else:
				product['price_unit'] = float(filtered_prices[0])
		else:
			# If cost price exists → keep that instead of PO price
			product['price_unit'] = product['standard_price']

		return product

	def find_product_quantity(self, product, row, purchase_line_column_values):
		"""
		Update the product quantity based on the extracted row and values.
		:param product: Product information.
		:param row: Extracted row from the table.
		:param purchase_line_column_values: Values extracted from the table.
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
		for qty in filtered_quantity:
			if float(qty) == product['standard_price']:
				filtered_quantity.remove(qty)
				break
		filtered_quantity = [qty for qty in filtered_quantity if
		                     str(qty) != product['default_code']]
		# Update the product quantity based on matches with extracted quantities
		product_qty = [float(qty) for qty in filtered_quantity if
		               qty in purchase_line_column_values.get('product_qty', [])]
		product['product_qty'] = max(product_qty) if product_qty else (
			max(filtered_quantity) if filtered_quantity else 1.0)
		return product

	def find_product_tax(self, product, row, purchase_line_column_values):
		"""
		Update the product tax based on the extracted row and values.
		:param product: Product information.
		:param row: Extracted row from the table.
		:param purchase_line_column_values: Values extracted from the table.
		:return: Updated product information.
		"""
		# Retrieve relevant tax configurations and tax rates
		purchase_digitization = self.env['purchase.digitization'].search(
			[('active_configuration', '=', True)])
		purchase_tax = self.env['account.tax'].search(
			[('active', '=', True), ('type_tax_use', '=', 'purchase')])
		row = list(row)
		# Extract percentage numbers from the row
		if purchase_digitization.tax_type == 'tax_per_line':
			percentage_numbers = (
				re.findall(r'\d+(?:\.\d+)?%', str(row).strip()))
			if 'taxes_id' in purchase_line_column_values.keys():
				actual_tax = [percentage for percentage in percentage_numbers if
				              percentage in purchase_line_column_values[
								  'taxes_id']]
			else:
				actual_tax = percentage_numbers
		else:
			actual_tax = purchase_line_column_values['taxes_id'] if \
				'taxes_id' in purchase_line_column_values.keys() else []
			# Update the product tax based on the actual tax values
		for tax in actual_tax:
			formatted_tax = float(tax.strip('%'))
			for p_tax in purchase_tax:
				if formatted_tax == p_tax.amount:
					product['taxes_id'] = [p_tax.id]
		return product

	def find_product_discount(self, product, row, purchase_line_column_values):
		"""
		Update the product discount based on the extracted row and values.
		:param product: Product information.
		:param row: Extracted row from the table.
		:param purchase_line_column_values: Values extracted from the table.
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
			if float(disc) == product['standard_price']:
				filtered_discount.remove(disc)
				break
		filtered_discount = [qty for qty in filtered_discount if
		                     str(qty) != product['default_code']]
		# Update the product discount based on matches with extracted discounts
		if 'discount' in purchase_line_column_values.keys():
			product_discount = [float(qty) for qty in filtered_discount if
			                    qty in purchase_line_column_values['discount']]
		else:
			product_discount = []
		product['discount'] = max(
			product_discount) if product_discount else 0.00
		return product

	def action_create_products(self, combined_table,
	                           purchase_line_column_values):
		"""
		Create products based on the combined table data.
		:param combined_table: Combined table data.
		:param purchase_line_column_values: Values extracted from the table.
		:return: List of created products by OCR.
		"""
		# Fetch invoice digitization configuration
		purchase_digitization = self.env['purchase.digitization'].search(
			[('active_configuration', '=', True)])
		# Check if product creation type is 'create_product'
		if purchase_digitization.product_creation_type == 'create_product':
			if not combined_table.empty:
				# Extract relevant columns based on configured keywords
				columns_to_keep = []
				df = combined_table
				for col in df.columns:
					values = df[col].tolist()
					cleaned_values = [str(item).replace('\n', '') for item in
					                  values]
					cleaned_values = [str(item).replace('\xa0', ' ') for item in
					                  cleaned_values]
					keywords = set(
						keyword.name.lower() for field in
						purchase_digitization.purchase_line_field_details_ids
						if field.purchase_line_field_id.name in [
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
					purchase_digitization.purchase_line_field_details_ids if
					field.purchase_line_field_id.name in field_names_to_check
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
					cleaned_split_row = [
						re.sub(special_char_pattern, '', item) for item in
						split_row]
					price_in_row = [float(num) for num in cleaned_split_row if
					                re.match(r'-?\d+\.\d+', num)]

					price_on_row = [
						float(num) for num in cleaned_split_row if
						'%' not in num and re.match(r'\d', num)]
					if price_in_row or price_on_row:
						final_table_rows.append(row)
				final_product_details = []
				ocr_products = []
				# extract the product code and name to create the product
				for row in final_table_rows:
					assumed_product_name = []
					product_code = ''
					for item in row:
						for value in purchase_line_column_values['product_id']:
							if value.lower() in item.lower():
								column_keys = [
									key for key in
									purchase_line_column_values.keys()]
								split_value = value.split()
								if 'default_code' not in column_keys:
									for val in split_value:
										if val in [split_value[0],
										           split_value[-1]]:
											if re.match(r'^[a-zA-Z0-9]+$',
											            val) and re.search(
												r'\d', val):
												product_code = val
											elif re.match(
												r'^[a-zA-Z0-9!@#$%^&*\[\]_]+$',
												val) and not val.isalpha():
												product_code = val
											elif re.match(
												r'^[0-9]+$',
												val) and not val.isalpha():
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
										 purchase_line_column_values[
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
					if not price_in_row:
						price_in_row = [float(num) for num in
						                cleaned_split_numerical_row if
						                '%' not in num and re.match(r'\d+',
						                                            num)]
					assumed_product_price = max(
						price_in_row) if price_in_row else 0
					assumed_product_name = [' '.join(item.split()) for item in
					                        assumed_product_name]
					if assumed_product_name:
						# Strip trailing dates (e.g. '05/30/2026 05:30:00') that get merged into the product name
						assumed_product_name[0] = re.sub(r'\s*\b[(]?\d{2}[/\-]\d{2}[/\-]\d{2,4}\b.*', '', assumed_product_name[0]).strip()
					
					product_details = {
						'name': assumed_product_name[0], 'ocr_product': True,
						'detailed_type': 'product'} if assumed_product_name \
						else {'name': None, 'ocr_product': True, }
					product_details['standard_price'] = \
						assumed_product_price if assumed_product_price else None
					product_details[
						'default_code'] = assumed_product_code[
						0] if assumed_product_code else None
					final_product_details.append(product_details)
					# Create the product by extracting details.
				for details in final_product_details:
					ocr_product = self.env['product.product'].create([details])
					ocr_products.append(ocr_product)
				return ocr_products

	def _make_ai_request(self, text, conversation_history):
		"""Try OLG first; fall back to OpenAI if an API key is configured."""
		config_parameter = self.env['ir.config_parameter'].sudo()
		olg_api_endpoint = config_parameter.get_param(
			'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
		try:
			response = iap_tools.iap_jsonrpc(
				olg_api_endpoint + "/api/olg/1/chat", params={
					'prompt': text,
					'conversation_history': conversation_history or [],
					'version': release.version,
				}, timeout=30)
			if response.get('status') == 'success':
				return response.get('content')
		except Exception as exc:
			logging.error(f"OLG request failed: {exc}")
		open_ai_key = config_parameter.get_param(
			'cyllo_invoice_digitization.digitization_openai_key', False)
		if open_ai_key:
			return self._make_gpt_request(open_ai_key, text, conversation_history)
		return None

	@staticmethod
	def _make_gpt_request(api_key, prompt, conversation_history):
		"""Send a request to OpenAI GPT as a fallback."""
		if not _OpenAI:
			logging.error("openai package is not installed.")
			return None
		try:
			client = _OpenAI(api_key=api_key)
			messages = conversation_history + [{"role": "user", "content": prompt}]
			response = client.chat.completions.create(
				model=GPT_MODEL, messages=messages, temperature=0)
			return response.choices[0].message.content
		except _AuthError:
			logging.error("Invalid OpenAI API key for purchase digitization.")
			return None
		except Exception as exc:
			logging.error(f"GPT fallback error: {exc}")
			return None

	def action_retry_digitization(self):
		"""
				Retry the digitization process by resetting order lines and
				triggering digitization.
				"""
		self.order_line = None
		self.action_send_digitization()
		if self.ocr_digitize_failed:
			return {
				'name': 'AI Digitization',
				'type': 'ir.actions.act_window',
				'res_model': 'digitization.ai.wizard',
				'view_mode': 'form',
				'target': 'new',
				'context': {'default_active_id': self.id},
			}

	def get_details_ai(self, text):
		"""
			Uses AI to extract detailed purchase quotation information,
			product specifics, and pricing from the provided text.
			:param text: Text content to extract information from.
			:return: Extracted information as a string.
			"""
		company_name = self.env.company.name
		try:
			conversation_history = [
				{'role': 'user',
				 'content':
					 f'Please extract detailed purchase quotation information, '
					 f'product specifics, and pricing from a provided PDF file.'
					 f' Your task involves capturing key data such as the '
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
					 f' stated on the quotation. Any errors found during this'
					 f' process can be rectified by pinpointing the mistake'
					 f' and making the necessary corrections.When identifying'
					 f' the correct partner name for billing purposes, it is'
					 f' essential to consider the individual or company to '
					 f'whom the purchase quotation is addressed. Ensure that '
					 f'the context aligns with the customer address provided'
					 f' and avoid using {company_name} in this process.'
				 }]
			content = self._make_ai_request(text, conversation_history)
			if content:
				return content
			self.ocr_digitize_failed = True
			self.ocr_digitize_completed = False
			self.write({'ocr_digitize_message': _(
				"Data cannot be read, digitization failed.")})
		except Exception as ecx:
			self.ocr_digitize_failed = True
			self.ocr_digitize_completed = False
			self.write({'ocr_digitize_message': _(
				"The AI Failed to Digitize the Document.")})
			logging.error(f"AccessError details: {ecx}")

	def get_quotation_details(self, pdf_details):
		"""
			Extracts purchase quote details from the provided PDF text using AI
			 and returns the details as a dictionary.
			:param pdf_details: Text content of the PDF document containing the
			 purchase quote details.
			:return: Dictionary containing the extracted purchase quote details.
			"""
		pdf_details = '\n'.join(
			[line.strip() for line in pdf_details.splitlines() if
			 line.strip()])
		try:
			company_name = self.env.company.name
			conversation_history = [
				{'role': 'user',
				 'content': f"Find and extract purchase quote details, "
				            f"including partner name,vendor reference, "
				            f"payment terms, incoterm, incoterm location "
				            f"represented as a dictionary. When extracting the"
				            f" partner name do not include {company_name}."
				            f"The dictionary keys should correspond to "
				            f"partner_name,vendor_reference,payment_term,"
				            f"incoterm,incoterm_location.If the values are null"
				            f",assign a blank value to the corresponding key."
				            f"The response should only contain the dictionary"
				            f" without any additional text."
				            f"(It must strictly follow these guidelines)"
				 }]
			content = self._make_ai_request(pdf_details, conversation_history)
			if content and isinstance(content, str):
				try:
					purchase_details = json.loads(content)
				except json.JSONDecodeError:
					start_index = content.find("{")
					end_index = content.find("}")
					extracted_quote_details = content[start_index:end_index + 1]
					purchase_details = json.loads(extracted_quote_details)
				return purchase_details
			self.ocr_digitize_failed = True
			self.ocr_digitize_completed = False
			self.write({'ocr_digitize_message': _(
				"Failed to extract the purchase quote details.")})
		except Exception as exc:
			self.ocr_digitize_failed = True
			self.ocr_digitize_completed = False
			self.write({'ocr_digitize_message': _(
				"The AI Failed to Digitize the Document.")})
			logging.error(f"AccessError details: {exc}")

	def get_product_details(self, pdf_details):
		"""
			Extracts product details from the provided PDF text using AI and
			returns the details as a list of dictionaries.
			:param pdf_details: Text content of the PDF document containing the
			 product details.
			:return: List of dictionaries containing the extracted
			product details.
			"""
		pdf_details = '\n'.join(
			[line.strip() for line in pdf_details.splitlines() if
			 line.strip()])
		purchase_digitization = self.env[
			'purchase.digitization'].search(
			[('active_configuration', '=', True)])
		try:
			if purchase_digitization.tax_type == 'tax_per_line':
				conversation_history = [
					{'role': 'user',
					 'content': f"Find and extract product details from this "
					            f"quotation,including product name,"
					            f"product code,quantity,product unit of "
					            f"measure,product price,product tax in "
					            f"percentage format with % symbol,discount. "
					            f"The dictionary keys should correspond to"
					            f" product_name(product name without "
					            f"product code),product_code, quantity,"
					            f"quantity_uom,price_unit, product_tax,"
					            f"discount.Add the each product details to"
					            f" the list as dictionary.The response should"
					            f" only contain the list of dictionary, the "
					            f"values of keys must be in string"
					            f"(in double quotes), no other text and the "
					            f"product name without product code needs "
					            f"strictly follow.(it must very very"
					            f"strictly follow) and do not return as python"
					            f" just as string(dont add new line command)."
					 }]
			else:
				conversation_history = [
					{'role': 'user',
					 'content': f"Find and extract product details from this "
					            f"quotation, including product name, "
					            f"product code,quantity, product unit of"
					            f" measure,product price,product tax in"
					            f" percentage format with % symbol and cosider"
					            f" single tax to all the product,discount."
					            f"The dictionary keys should correspond to"
					            f" product_name(product name without product"
					            f" code),product_code, quantity,quantity_uom, "
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
			content = self._make_ai_request(pdf_details, conversation_history)
			if content and isinstance(content, str):
				try:
					response_content = content.replace('\n', '').replace(",]", "]")
					quote_details = json.loads(response_content)
				except json.JSONDecodeError:
					response_content = content.replace('\n', '').replace(",]", "]")
					start_index = response_content.find("[")
					end_index = response_content.rfind("]")  # rfind to get the LAST ]
					if start_index == -1 or end_index == -1:
						logging.error("Product details: no JSON list found in AI response")
						return None
					extracted_quote_details = response_content[
						start_index:end_index + 1]
					quote_details = json.loads(extracted_quote_details)
				# If AI wrapped result in a dict, try to unwrap the list
				if isinstance(quote_details, dict):
					for val in quote_details.values():
						if isinstance(val, list):
							quote_details = val
							break
					else:
						quote_details = [quote_details]
				if not isinstance(quote_details, list):
					logging.error("Product details: unexpected AI response format")
					return None
				return quote_details
			self.ocr_digitize_failed = True
			self.ocr_digitize_completed = False
			self.write({'ocr_digitize_message': _(
				"Failed to extract the Product details.")})
		except Exception as exc:
			self.write({'ocr_digitize_message': _(
				"The AI Failed to Digitize the Document.")})
			logging.error(f"AccessError details: {exc}")

	def find_partner_ai(self, text, quotation_details):
		"""
		Find a partner based on the extracted text from pdf and create a
		partner if not exist.
		:param text: Extracted text to search for partner information.
		:param quotation_details: Dictionary containing details extracted from
		the pdf using AI Functionality."""
		# Positional heuristic first — avoids matching own company contacts
		vendor_name = self._extract_vendor_from_text(text)
		partner_name = (
			quotation_details.get('partner_name') if quotation_details else ''
		) or ''
		partner_name = partner_name.strip()
		for candidate in (vendor_name, partner_name):
			candidate = (candidate or '').strip()
			if not candidate:
				continue
			partner = self.env['res.partner'].search(
				[('name', '=ilike', candidate)], limit=1)
			if partner:
				self.write({'partner_id': partner.id})
				return
		create_name = partner_name or (vendor_name or '').strip()
		if create_name:
			partner = self.env['res.partner'].create({'name': create_name})
			self.write({'partner_id': partner.id})
			return
		# Fallback: substring scan excluding own company and internal users
		internal_users = self.env['res.users'].search([('share', '=', False)])
		internal_partner_ids = internal_users.mapped('partner_id').ids
		internal_partner_ids.append(self.env.company.partner_id.id)
		partner_ids = self.env['res.partner'].search(
			[('id', 'not in', internal_partner_ids)])
		normalized_text = ' '.join(text.split())
		found_partners = partner_ids.filtered(
			lambda partner: partner.name
			and re.search(rf'\b{re.escape(partner.name)}\b',
			              normalized_text, re.I))
		if found_partners:
			found_partners = found_partners.sorted(
				key=lambda partner: len(partner.name or ''), reverse=True)
			self.write({'partner_id': found_partners[0].id})

	def action_find_field_values_ai(self, text, quotation_details):
		"""
			Finds field values in the provided text based on the quotation
			details and updates the purchase order accordingly.
			:param text: Text content to search for field values.
			:param quotation_details: Dictionary containing details extracted
			from the quotation.
			"""
		if not quotation_details:
			return
		if quotation_details.get('vendor_reference'):
			self.write(
				{'partner_ref': quotation_details['vendor_reference']})
		if quotation_details.get('payment_term'):
			payment_terms = self.payment_term_id.search([])
			found_term = [term for term in payment_terms if
			              term.name.lower() == quotation_details[
							  'payment_term'].lower()] if payment_terms \
				else None
			if found_term:
				self.write({'payment_term_id': found_term[0].id})
			else:
				found_term_in_text = [term for term in payment_terms if
				                      term.name.lower() in text.lower()] \
					if payment_terms else None
				if found_term_in_text:
					self.write({'payment_term_id': found_term_in_text[0].id})
		if quotation_details.get('incoterm'):
			incoterms = self.incoterm_id.search(
				[('code', '=', quotation_details['incoterm'])])
			if incoterms:
				self.write({'incoterm_id': incoterms[0].id})
			else:
				incoterms = self.incoterm_id.search([])
				found_incoterm = [term for term in incoterms if
				                  term.code in text] if incoterms else None
				if found_incoterm:
					self.write({'incoterm_id': found_incoterm[0].id})
		if quotation_details.get('incoterm_location'):
			self.write(
				{'incoterm_location': quotation_details['incoterm_location']})

	def action_find_product(self, product_details):
		"""
			Finds or creates products based on the provided product details and
			 adds them to the purchase order.
			:param product_details: List of dictionaries containing details of
			 the products to be found or created.
			"""
		if not product_details:
			return
		# Remove exact duplicates from AI response (same name+code+qty+price+tax+discount).
		# Keeps legitimate same-product lines that differ in quantity or price.
		seen_keys = set()
		deduped = []
		for item in product_details:
			if not isinstance(item, dict):
				continue
			key = (
				str(item.get('product_name', '') or '').lower().strip(),
				str(item.get('product_code', '') or '').lower().strip(),
				str(item.get('quantity', '') or '').strip(),
				str(item.get('price_unit', '') or '').strip(),
				str(item.get('product_tax', '') or '').strip(),
				str(item.get('discount', '') or '').strip(),
			)
			if key not in seen_keys:
				seen_keys.add(key)
				deduped.append(item)
		product_details = deduped
		products = self.env['product.product'].search([])
		supplier_products_details = self.env['product.supplierinfo'].search([])
		for rec in product_details:
			if not isinstance(rec, dict):
				continue
			product_code = rec.get('product_code', '') or ''
			raw_product_name = rec.get('product_name', '') or ''
			# Sanitize AI responses that include Dates in product names
			product_name = re.sub(r'\s*\b[(]?\d{2}[/\-]\d{2}[/\-]\d{2,4}\b.*', '', raw_product_name).strip()
			quote_details = {
				'order_id': self.id,
				'product_id': None,
				'product_qty': 1,
			}
			supplier_by_code = [supplier for supplier in
			                    supplier_products_details if
			                    supplier.product_code and
			                    supplier.product_code.lower() == product_code.lower()] \
				if product_code and supplier_products_details else []
			supplier_by_code = self.env['product.supplierinfo'].search(
				[('id', 'in', [spr.id for spr in supplier_by_code])])
			products_by_supplier_code = supplier_by_code.mapped(
				'product_tmpl_id') if supplier_by_code else []
			products_by_supplier_code = self.env['product.product'].search(
				[('product_tmpl_id', 'in', [product.id for product in
				                            products_by_supplier_code])]) if products_by_supplier_code else []
			if not products_by_supplier_code:
				products_by_supplier_code = supplier_by_code.mapped(
					'product_id') if supplier_by_code else []
			products_by_name = [
				product for product in products if
				product_name.lower() == product.name.lower()] \
				if not products_by_supplier_code and product_name else []
			# Search by display name when exact name gives 0 or >1 results
			products_by_display_name = [
				product for product in products
				if product_name.lower() in product.display_name.lower()
			] if product_name and len(products_by_name) != 1 and not products_by_supplier_code else []
			if products_by_supplier_code:
				quote_details['product_id'] = products_by_supplier_code[0].id
			elif len(products_by_name) == 1:
				quote_details['product_id'] = products_by_name[0].id
			elif products_by_display_name:
				quote_details['product_id'] = products_by_display_name[0].id

			# Extracting quantity from the product details
			qty_val = rec.get('quantity', '')
			qty_match = re.search(r'\d+(\.\d+)?', str(qty_val)) if qty_val else None
			if qty_match:
				quote_details['product_qty'] = float(qty_match.group(0))
			# Extracting unit of measure from the product details if available
			uom_list = self.env['uom.uom'].search([])
			quantity_uom = rec.get('quantity_uom', '') or ''
			found_uom = [uom for uom in uom_list if
			             uom.name == quantity_uom] if quantity_uom and uom_list else []
			if found_uom:
				quote_details['product_uom'] = found_uom[0].id

			# Extracting product price from the product details
			price_val = rec.get('price_unit', '') or ''
			price_unit = str(price_val).replace(',', '')
			price_match = re.search(r'\d+(\.\d+)?', price_unit) if price_unit else None
			if price_match:
				quote_details['price_unit'] = float(price_match.group(0))

			# Extracting product tax from the product details
			tax_list = self.env['account.tax'].search(
				[('active', '=', True), ('type_tax_use', '=', 'purchase')])
			product_tax_val = rec.get('product_tax', '') or ''
			tax_rate = product_tax_val.rstrip('%') if product_tax_val else '0'
			try:
				tax_rate_float = float(tax_rate)
			except (ValueError, TypeError):
				tax_rate_float = 0.0
			product_tax = [tax for tax in tax_list if
			               tax.amount == tax_rate_float] if tax_list else []
			quote_details['taxes_id'] = [
				product_tax[0].id] if product_tax else None

			# Extracting product discount from the product details
			discount_val = rec.get('discount', '') or ''
			discount_match = re.search(r'\d+(\.\d+)?', str(discount_val)) if discount_val else None
			quote_details['discount'] = float(
				discount_match.group(0)) if discount_match else 0.0
			if quote_details['product_id']:
				self.order_line.create(quote_details)
			else:
				self.action_create_product_ai(rec, quote_details)
			if self.order_line:
				self.ocr_digitize_completed = True
			if self.ocr_digitize_completed:
				self.ocr_digitize_failed = False if (
					self.ocr_digitize_failed) else False

	def action_create_product_ai(self, product_details, quote_details):
		"""
			Creates a product based on the provided product and quote details.
			:param product_details: Dictionary containing details of the product
			 to be created.
			:param quote_details: Dictionary containing details of the quote.
			"""
		purchase_digitization = self.env[
			'purchase.digitization'].search(
			[('active_configuration', '=', True)])
		if purchase_digitization.product_creation_type == 'create_product':
			if product_details.get('product_name'):
				product_values = {
					'name': product_details.get('product_name'),
					'ocr_product': True,
					'detailed_type': 'product'
				}
				price_unit = quote_details.get('price_unit', None)
				if price_unit is not None:
					product_values['standard_price'] = quote_details[
						'price_unit']
				uom_unit = quote_details.get('product_uom', None)
				if uom_unit is not None:
					product_values['uom_id'] = quote_details['product_uom']
					product_values['uom_po_id'] = quote_details[
						'product_uom']
				product_id = self.env['product.product'].create(product_values)
				quote_details['product_id'] = product_id.id
				self.order_line.create(quote_details)

	@staticmethod
	def _norm_alnum(s):
		return re.sub(r'[^a-z0-9]', '', (s or '').lower())

	def _match_partner_from_block(self, partners, block):
		"""Best existing partner for a counterparty block, combining name and
		VAT: exact name first, then VAT (narrowed by name when several partners
		share a VAT), then a loose name match. Empty recordset when none."""
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

	def _detect_counterparty_block(self, text, company):
		"""Return the counterparty address block ``{name, vat, street, zip}`` or
		``None``. The first address block whose address and name are NOT our own
		company is the vendor. Same rule as the invoice digitization module."""
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
		          'tax', 'date', 'source', 'purchase order', 'quotation',
		          'invoice', 'page', 'subtotal')
		for index, line in enumerate(lines):
			if index < 1 or not street_re.match(line):
				continue
			name = lines[index - 1].strip().rstrip(',').strip()
			if (street_re.match(name) or re.search(r'\d{3,}', name)
					or len(name) < 3
					or any(word in name.lower() for word in reject)):
				continue
			window = lines[index - 1:index + 5]
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

	def _extract_lines_from_pdf_text(self, file_path):
		"""Parse product lines directly from the PO/bill text table (clean,
		camelot-independent). Same logic as the invoice digitization module."""
		out = []
		try:
			all_lines = []
			with pdfplumber.open(file_path) as pdf:
				for page in pdf.pages:
					t = page.extract_text() or ''
					all_lines.extend(t.split('\n'))
		except Exception:
			return out
		hdr = None
		for i, ln in enumerate(all_lines):
			low = ln.lower()
			if ('description' in low or 'product' in low or 'item' in low) and \
			   ('quantity' in low or 'qty' in low or 'price' in low):
				hdr = i
				break
		if hdr is None:
			return out
		stop_words = ('untaxed amount', 'subtotal', 'sub total', 'total',
		              'tax ', 'amount due', 'balance', 'page ', 'thank you')
		row_re = re.compile(
			r'^(?P<name>.+?)\s+'
			r'(?P<qty>\d[\d,]*(?:\.\d+)?)\s+'
			r'(?P<price>[\d,]+\.\d{2})\s+'
			r'(?:(?P<tax>\d+(?:\.\d+)?)\s*%\s+)?'
			r'[^\d\-]*'
			r'(?P<amount>[\d,]+\.\d{2})\s*$')
		for ln in all_lines[hdr + 1:]:
			s = ln.strip()
			low = s.lower()
			if not s:
				continue
			if any(sw in low for sw in stop_words):
				break
			mt = row_re.match(s)
			if mt:
				out.append({
					'name': mt.group('name').strip(),
					'quantity': float(mt.group('qty').replace(',', '')),
					'price_unit': float(mt.group('price').replace(',', '')),
					'tax': mt.group('tax'),
				})
		return out

	def _create_po_lines_from_parsed(self, parsed_lines):
		"""Create purchase.order.line records from parsed line dicts, matching
		or creating products and mapping the tax percentage."""
		Product = self.env['product.product']
		pdig = self.env['purchase.digitization'].search(
			[('active_configuration', '=', True)], limit=1)
		create_ok = (not pdig) or pdig.product_creation_type == 'create_product'
		for p in parsed_lines:
			raw = re.sub(r'^[A-Za-z]*\d+\s*[:\-]\s*', '', p['name']).strip()
			# Strip appended dates like 05/30/2026 05:30:00
			raw = re.sub(r'\s*\b[(]?\d{2}[/\-]\d{2}[/\-]\d{2,4}\b.*', '', raw).strip()
			parts = raw.split('] ')
			if len(parts) > 1:
				name, code = parts[1].strip(), parts[0].lstrip('[').strip()
			else:
				name, code = raw, None
			product = Product
			if code:
				product = Product.search([('default_code', '=', code)], limit=1) \
					or Product.search([('default_code', 'ilike', code)], limit=1) \
					or Product.search([('barcode', '=', code)], limit=1)
			if not product and name:
				product = Product.search([('name', '=', name)], limit=1) \
					or Product.search([('name', 'ilike', name)], limit=1)
			if not product and create_ok:
				vals = {'name': name}
				if code:
					vals['default_code'] = code
				product = Product.create(vals)
			if not product:
				continue
			line_vals = {
				'order_id': self.id,
				'product_id': product.id,
				'name': product.display_name,
				'product_qty': p.get('quantity', 1.0),
				'price_unit': p.get('price_unit', 0.0),
				'product_uom': (product.uom_po_id or product.uom_id).id,
				'date_planned': fields.Datetime.now(),
			}
			if p.get('tax'):
				tax = self.env['account.tax'].search(
					[('type_tax_use', '=', 'purchase'),
					 ('amount', '=', float(p['tax'])),
					 ('amount_type', '=', 'percent')], limit=1)
				if tax:
					line_vals['taxes_id'] = [(6, 0, tax.ids)]
			self.env['purchase.order.line'].create(line_vals)

	def _extract_vendor_from_text(self, text):
		"""Extract vendor name from PDF text. Primary rule: the address block
		that is not our company. Fallback: scan backwards from the product-table
		header (vendor block sits just before it)."""
		block = self._detect_counterparty_block(text, self.env.company)
		if block:
			return block['name']
		company_name = self.env.company.name
		skip_names = {company_name.lower()}
		internal_users = self.env['res.users'].search([('share', '=', False)])
		for user in internal_users:
			if user.partner_id and user.partner_id.name:
				skip_names.add(user.partner_id.name.lower())
		company_partner = self.env.company.partner_id
		if company_partner:
			for child in company_partner.child_ids:
				if child.name:
					skip_names.add(child.name.lower())
		skip_exact = {'united states', 'usa', 'india', 'united kingdom', 'uk',
		              'australia', 'canada', 'germany', 'france', 'suite',
		              'vendor bill', 'invoice', 'purchase order', 'quotation',
		              'bill to', 'ship to', 'sold to', 'from', 'to'}
		skip_exact.update(skip_names)
		skip_contains = {'bill/', 'date', 'payment', 'source', 'reference',
		                 'incoterm', 'fiscal', 'due', 'term', 'attn',
		                 'attention', 'tel:', 'fax:', 'email', 'phone',
		                 'www.', 'http', 'vendor bill', 'invoice no',
		                 'purchase order', 'p.o.', 'po #', 'order #'}
		table_markers = {'description', 'qty', 'quantity', 'unit price',
		                 'order lines', 'products', 'line items'}
		lines = [l.strip() for l in text.splitlines() if l.strip()]
		table_idx = next(
			(i for i, l in enumerate(lines)
			 if any(kw in l.lower() for kw in table_markers)), len(lines))
		company_idx = next(
			(i for i, l in enumerate(lines)
			 if company_name.lower() in l.lower()), -1)
		start = company_idx + 1 if company_idx != -1 else 0
		for line in reversed(lines[start:table_idx]):
			low = line.lower()
			if low in skip_exact:
				continue
			if any(kw in low for kw in skip_contains):
				continue
			if re.search(r'\d', line):
				continue
			if len(line) < 3:
				continue
			return line
		return None

	def _extract_products_from_table(self, table_data,
	                                  purchase_line_column_values=None):
		"""Fallback: extract products from table rows using configured keywords
		to identify the product, qty, and price columns."""
		_SKIP = {'total', 'tax', 'untaxed', 'subtotal', 'discount', 'amount',
		         'description', 'qty', 'quantity', 'price', 'unit', 'item',
		         'no', 'sr', '#', 'product', 'code', 'hsn',
		         'vendor', 'invoice', 'bill', 'purchase order', 'quotation',
		         'date', 'from', 'to', 'reference', 'payment', 'source',
		         'journal', 'currency', 'fiscal', 'due', 'term', 'narration',
		         'note', 'remark', 'memo', 'contact', 'address', 'company'}
		purchase_digitization = self.env['purchase.digitization'].search(
			[('active_configuration', '=', True)])
		# Collect configured keywords per field
		product_kws, qty_kws, price_kws = [], [], []
		for field in purchase_digitization.purchase_line_field_details_ids:
			fname = field.purchase_line_field_id.name
			kws = [k.name.lower() for k in field.line_field_keyword_ids]
			if fname in ('product_id', 'default_code'):
				product_kws.extend(kws)
			elif fname == 'product_qty':
				qty_kws.extend(kws)
			elif fname == 'price_unit':
				price_kws.extend(kws)
		# Already-extracted values from action_get_purchase_line_columns
		plcv = purchase_line_column_values or {}
		extracted_qtys = plcv.get('product_qty', [])
		extracted_prices = plcv.get('price_unit', [])
		for tbl_rows in table_data:
			if not tbl_rows:
				continue
			# Find header row and column indices using configured keywords
			header_idx = None
			prod_col = qty_col = price_col = None
			for r_idx, row in enumerate(tbl_rows):
				for c_idx, cell in enumerate(row):
					cl = str(cell).lower().strip()
					if product_kws and any(kw in cl for kw in product_kws):
						header_idx = r_idx
						prod_col = c_idx
					if qty_kws and any(kw in cl for kw in qty_kws) and qty_col is None:
						qty_col = c_idx
					if price_kws and any(kw in cl for kw in price_kws) and price_col is None:
						price_col = c_idx
				if header_idx is not None:
					break
			# Defaults when config keywords not found
			if prod_col is None:
				prod_col = 0
			data_rows = tbl_rows[header_idx + 1:] if header_idx is not None else tbl_rows
			prod_idx = 0
			for row in data_rows:
				if prod_col >= len(row):
					continue
				product_name = str(row[prod_col]).strip()
				if not product_name or len(product_name) < 2:
					continue
				if any(kw in product_name.lower() for kw in _SKIP):
					continue
				# Skip date patterns, bill/invoice references, and pure numbers
				if re.match(r'^\d{2}[/\-]\d{2}[/\-]\d{4}$', product_name):
					continue
				if re.match(r'^[A-Z]+/\d{4}/', product_name):
					continue
				if not re.search(r'[a-zA-Z]', product_name):
					continue
				# Qty: from already-extracted values or from table column
				if extracted_qtys and prod_idx < len(extracted_qtys):
					try:
						qty = float(str(extracted_qtys[prod_idx]).replace(',', ''))
					except (ValueError, TypeError):
						qty = 1.0
				elif qty_col is not None and qty_col < len(row):
					m = re.search(r'\d+\.?\d*', str(row[qty_col]).replace(',', ''))
					qty = float(m.group()) if m else 1.0
				else:
					nums = [float(m.group()) for c in row[1:]
					        for m in [re.search(r'^\d+\.?\d*$',
					                            str(c).replace(',', ''))] if m]
					qty = nums[0] if nums else 1.0
				# Price: from already-extracted values or from table column
				if extracted_prices and prod_idx < len(extracted_prices):
					try:
						price = float(str(extracted_prices[prod_idx]).replace(',', ''))
					except (ValueError, TypeError):
						price = 0.0
				elif price_col is not None and price_col < len(row):
					m = re.search(r'\d+\.?\d*', str(row[price_col]).replace(',', ''))
					price = float(m.group()) if m else 0.0
				else:
					nums = [float(m.group()) for c in row[1:]
					        for m in [re.search(r'^\d+\.?\d*$',
					                            str(c).replace(',', ''))] if m]
					price = nums[1] if len(nums) > 1 else 0.0
				product = self.env['product.product'].search(
					[('name', '=ilike', product_name)], limit=1)
				if not product and (
						purchase_digitization.product_creation_type ==
						'create_product'):
					product = self.env['product.product'].create(
						{'name': product_name, 'detailed_type': 'product'})
				if product:
					self.order_line.create({
						'order_id': self.id,
						'product_id': product.id,
						'product_qty': qty,
						'price_unit': price,
					})
					self.ocr_digitize_completed = True
					self.ocr_digitize_failed = False
					self.write({'ocr_digitize_message': ''})
				prod_idx += 1

	def _extract_products_from_text(self, text):
		"""Last resort: parse PDF text for product rows.
		Uses configured purchase line keywords to locate the table header;
		falls back to common keywords when none are configured."""
		_STOP_KWORDS = {'subtotal', 'sub-total', 'untaxed amount',
		                'untaxed', 'tax 1', 'total'}
		_SKIP = {'total', 'tax', 'untaxed', 'subtotal', 'discount', 'amount',
		         'qty', 'quantity', 'price', 'unit', 'item', 'description',
		         'no', 'sr', '#', 'product', 'code', 'hsn', 'invoice', 'bill',
		         'date', 'payment', 'taxes', 'source',
		         'vendor', 'purchase order', 'quotation',
		         'from', 'to', 'reference', 'journal', 'currency',
		         'fiscal', 'due', 'term', 'note', 'remark', 'memo',
		         'contact', 'address', 'company', 'narration'}
		purchase_digitization = self.env['purchase.digitization'].search(
			[('active_configuration', '=', True)])
		# Build header keywords from config; fall back to common defaults
		_HEADER_KWORDS = set()
		for field in purchase_digitization.purchase_line_field_details_ids:
			if field.purchase_line_field_id.name in ('product_id', 'default_code'):
				for kw in field.line_field_keyword_ids:
					_HEADER_KWORDS.add(kw.name.lower())
		if not _HEADER_KWORDS:
			_HEADER_KWORDS = {'description', 'product', 'item', 'particulars'}
		lines = [l.strip() for l in text.splitlines() if l.strip()]
		header_idx = next(
			(i for i, line in enumerate(lines)
			 if any(kw in line.lower() for kw in _HEADER_KWORDS)), -1)
		if header_idx == -1:
			return
		tokens = []
		for line in lines[header_idx + 1:]:
			low = line.lower().strip()
			if any(kw in low for kw in _STOP_KWORDS):
				break
			tokens.append(line.strip())
		pending_name = []
		pending_nums = []
		candidates = []
		for tok in tokens:
			cleaned = re.sub(r'[,%$₹€£]', '', tok)
			is_num = bool(re.match(r'^\d+\.?\d*$', cleaned) and cleaned)
			if is_num:
				try:
					pending_nums.append(float(cleaned))
				except ValueError:
					pass
			else:
				if pending_name and pending_nums:
					candidates.append((' '.join(pending_name), pending_nums[:]))
					pending_name = []
					pending_nums = []
				low_tok = tok.lower()
				if not any(kw in low_tok for kw in _SKIP) and len(tok) >= 2:
					pending_name.append(tok)
		if pending_name and pending_nums:
			candidates.append((' '.join(pending_name), pending_nums[:]))
		for product_name, nums in candidates:
			if any(kw in product_name.lower() for kw in _SKIP):
				continue
			product = self.env['product.product'].search(
				[('name', '=ilike', product_name)], limit=1)
			if not product and (
					purchase_digitization and
					purchase_digitization.product_creation_type ==
					'create_product'):
				product = self.env['product.product'].create(
					{'name': product_name, 'detailed_type': 'product'})
			if product:
				qty = nums[0] if nums else 1.0
				price = nums[1] if len(nums) > 1 else 0.0
				self.order_line.create({
					'order_id': self.id,
					'product_id': product.id,
					'product_qty': qty,
					'price_unit': price,
				})
				self.ocr_digitize_completed = True
				self.ocr_digitize_failed = False
				self.write({'ocr_digitize_message': ''})
