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
from collections import defaultdict

import base64
import codecs
import os
import tempfile
import pandas as pd
from datetime import datetime
from io import BytesIO
from ofxparse import OfxParser
from PyQifParser.PyQifParser import PyQifParser

from odoo import _, fields, models
from odoo.exceptions import ValidationError


def _get_date_value(file_type, row):
    """
        Get the date value based on the file type.

        Args:
            file_type (str): The type of the file ('.xlsx', '.xls' or 'csv').
            row (pandas.Series): The row containing the data.

        Returns:
            datetime.date: The date value.

        Raises:
            ValueError: If an unsupported file type is provided.
    """
    if not row.get('Date'):
        raise ValidationError(_("Required Value Date is Missing in your uploaded sheet"))
    if file_type in {'.xlsx', '.xls'}:
        return fields.date.today() if pd.isna(row.get('Date')) else row.get('Date').date()
    else:
        date_obj = str(fields.date.today()) if pd.isna(row.get('Date')) else row.get('Date')
        return datetime.strptime(date_obj, "%Y-%m-%d")


def _validate_row_data(row, index):
    """
        Validate the data in a row.

        Args:
            row (pandas.Series): The row containing the data.
            index (int): The index of the row in the dataset.

        Raises:
        ValidationError: If a required field (Reference or Amount) is
        missing. Partner is optional for bank statement lines.
    """
    if pd.isna(row.get('Reference')):
        raise ValidationError(_("Required Value Reference is Missing in your uploaded sheet"))
    elif pd.isna(row.get('Amount')):
        raise ValidationError(_("Required Value Amount is Missing in your uploaded sheet"))


def validation_on_duplication_in_file(data_references, file):
    """
        Validate duplication in file references.

        Parameters:
        - data_references (list): List of references in the file.
        - file (str): File type ('.xlsx', '.xls', '.csv', '.ofx', '.qif').

        Raises:
        - ValidationError: If duplicate references are found.
    """
    reference_counts = defaultdict(int)
    if file in {'.xlsx', '.xls', '.csv'}:
        for record in data_references:
            reference = record['data']
            reference_counts[reference] += 1
        duplicate_references = [ref for ref, count in reference_counts.items() if count > 1]
        if duplicate_references:
            raise ValidationError(_(f"Duplicate reference error in your selected file: {duplicate_references}"))
    else:
        seen_references = set()
        duplicate_references = {record for record in data_references if
                                record in seen_references or seen_references.add(record)}
        if duplicate_references:
            raise ValidationError(
                _(f"Duplicate reference error in your selected file: {duplicate_references}"))


class ImportBankStatement(models.TransientModel):
    """ A class to import files as bank statement """
    _name = "import.bank.statement"
    _description = "Import button"
    _rec_name = "file_name"

    attachment = fields.Binary(string="File", required=True, help="Choose the file to import", attachment=False)
    file_name = fields.Char(help="Name of the file")
    journal_id = fields.Many2one('account.journal', string="Journal",
                                 help="Journal in which the file importing", required=True)

    def duplication_and_create_record(self, duplicate_keys, records_to_create):
        """
            Handle duplicate keys and create records.

            Args:
                duplicate_keys (list): List of duplicate keys.
                records_to_create (list): List of records to create.

            Raises:
                ValidationError: If there are duplicate keys, raise an error
                                with formatted duplicate keys. If there are
                                records to create, create them and save the
                                current database transaction.
        """
        if duplicate_keys:
            formatted_keys = ',\n'.join(key[0] for key in duplicate_keys)
            raise ValidationError(_(f"Duplicate key error:\n{formatted_keys}"))
        if records_to_create:
            for item in records_to_create:
                self.env['account.bank.statement'].create(item)
                self._cr.savepoint()

    def action_iterate_rows(self, file_type, data_file):
        """
           Process each row in the data file, validate, and create records.

           Args:
               file_type (str): The type of the file ('.xlsx' or '.xls' or
               '.csv').
               data_file (pandas.DataFrame): The DataFrame containing
               the data.

           Raises:
               ValidationError: If duplicate keys are found or if required data
               is missing.
       """
        duplicate_keys = []
        records_to_create = []
        data_file['Reference'] = data_file['Reference'].astype(str)
        for index, row in data_file.iterrows():
            query = "SELECT name FROM account_bank_statement WHERE name = %s"
            if row.get('Reference') != 'nan':
                self.env.cr.execute(query, (row['Reference'],))
            else:
                raise ValidationError(_("Required field value Reference is Missing in your uploaded sheet"))
            result = self.env.cr.fetchone()
            if result:
                duplicate_keys.append(result)
            else:
                _validate_row_data(row, index)
                # A bank statement line does not require a partner.  Resolve
                # one only when the optional Partner column has a value; this
                # also lets sheets omit that column entirely.
                partner_name = row.get('Partner')
                partner = self.env['res.partner']
                if pd.notna(partner_name) and str(partner_name).strip():
                    partner = self.env['res.partner'].search(
                        [('name', '=', str(partner_name).strip())], limit=1)
                file_type_suffix = (
                    '/xlsx file' if file_type == '.xlsx' else '/xls file' if file_type == '.xls' else '/csv file')
                payment_ref = f"import/Bnk/{_get_date_value(file_type, row).strftime('%Y-%m-%d')}{file_type_suffix}"
                # Collect data for creating a new record
                records_to_create.append({
                    'name': row.get('Reference'),
                    'line_ids': [fields.Command.create({
                        'date': _get_date_value(file_type, row),
                        'payment_ref': payment_ref,
                        'partner_id': partner.id,
                        'journal_id': self.journal_id.id,
                        'amount': row.get('Amount')})]
                })
        self.duplication_and_create_record(duplicate_keys, records_to_create)

    def parse_transaction(self, transaction_str):
        """
           Parse a transaction string and extract relevant information.

           Args:
               transaction_str (str): The transaction string containing information in a specific format.

           Returns:
               dict: A dictionary containing parsed transaction information with keys:
                   - 'type': Transaction type.
                   - 'date': Transaction date.
                   - 'amount': Transaction amount.
                   - 'partner': Transaction partner.
                   - 'name': Transaction name.
                   - 'end': End of transaction.

           Example:
               For a transaction string like:
                   '!Type:Bank\nD14/04/2023\nT2000.00\nPDeco Addict\nNJohn Doe\n '
               The function will return:
                   {'type': 'Bank',
                    'date': '14/04/2023',
                    'amount': '2000.00',
                    'partner': 'Deco Addict',
                    'name': 'John Doe',
                    'end': ''}
       """
        final_vals = {}
        lines = transaction_str.split("\n")
        for line in lines:
            if line.startswith('!Type:'):
                transaction_type = line[6:]
                final_vals['type'] = (transaction_type.strip())
            elif line.startswith('D'):
                date = line[1:]
                final_vals['date'] = (date.strip())
            elif line.startswith('T'):
                amount = line[1:]
                final_vals['amount'] = (amount.strip())
            elif line.startswith('P'):
                partner = line[1:]
                final_vals['partner'] = (partner.strip())
            elif line.startswith('N'):
                name = line[1:]
                final_vals['name'] = (name.strip())
            elif line.startswith(' '):
                end = line.strip()
                final_vals['end'] = (end.strip())
        return final_vals

    def convert_date_format(self, date_str):
        """Convert various date formats to dd/mm/yyyy"""
        date_str = date_str.strip()

        formats_to_try = [
            '%m/%d/%y', '%m/%d/%Y', '%d/%m/%y', '%d/%m/%Y',
            '%d-%m-%y', '%d-%m-%Y', '%Y-%m-%d', '%m.%d.%y'
        ]

        for date_format in formats_to_try:
            try:
                date_obj = datetime.strptime(date_str, date_format)
                return date_obj.strftime('%m.%d.%y')
            except ValueError:
                continue
        return date_str

    def action_statement_import(self):
        """
            Import statements from various file formats, including CSV, XLSX,
            XLS, OFX, and QIF.

            Raises:
                ValidationError: If the file format is incorrect or if there
                are errors in the file content.
        """
        split_tup = os.path.splitext(self.file_name)
        if split_tup[1] in {'.csv', '.xlsx', '.ofx', '.qif', '.xls'}:
            if split_tup[1] in {'.csv', '.xlsx', '.xls'}:
                # Reading csv file
                data_file = pd.read_csv(BytesIO(base64.b64decode(self.attachment))) if (
                        split_tup[1] == '.csv') else pd.read_excel(
                    BytesIO(base64.b64decode(self.attachment)))
                if 'Reference' not in data_file.columns:
                    raise ValidationError("Required Value Reference is Missing in your uploaded sheet")

                data_references = [{'index': index, 'data': rows['Reference']} for index, rows in data_file.iterrows()]
                validation_on_duplication_in_file(data_references, split_tup[1])
                self.action_iterate_rows(split_tup[1], data_file)
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Statements',
                    'view_mode': 'tree',
                    'res_model': 'account.bank.statement',
                }
            elif split_tup[1] == '.ofx':
                # Parsing the file
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.ofx') as tmp_file:
                        tmp_file.write(base64.b64decode(self.attachment))
                        file_path = tmp_file.name

                    with codecs.open(file_path, encoding='latin-1') as file_obj:
                        ofx_file = OfxParser.parse(file_obj)
                except Exception as e:
                    raise ValidationError(_("Wrong file format"))
                finally:
                    if 'file_path' in locals() and os.path.exists(file_path):
                        os.remove(file_path)

                if not ofx_file.account.routing_number:
                    raise ValidationError(_("No Reference information found in OFX file."))
                if not ofx_file.account:
                    raise ValidationError(_("No account information found in OFX file."))
                if not ofx_file.account.statement:
                    raise ValidationError(_("No statement information found in OFX file."))
                statement_list = []
                validation_on_duplication_in_file({ofx_file.account.routing_number}, split_tup[1])
                # Reading the content from file
                for transaction in ofx_file.account.statement.transactions:
                    if transaction.amount == 0:
                        continue
                    payee = transaction.payee
                    amount = transaction.amount
                    date = transaction.date if transaction.date else (fields.date.today())
                    partner = self.env['res.partner'].search([('name', '=', payee)])
                    if not partner:
                        raise ValidationError(_("Partner not exist"))
                    statement_list.append([partner.id, amount, date])
                self.action_ofx_or_qif(split_tup[1], statement_list, ofx_file)
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Statements',
                    'view_mode': 'tree',
                    'res_model': 'account.bank.statement',
                }
            elif split_tup[1] == '.qif':
                file_path = None
                try:
                    # Create temporary file with content
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.qif', mode='wb') as tmp_file:
                        tmp_file.write(base64.b64decode(self.attachment))
                        file_path = tmp_file.name

                    # Read and clean the QIF file
                    with open(file_path, 'r') as qif_file:
                        data = qif_file.readlines()

                    cleaned_data = []
                    for line in data:
                        stripped = line.strip()

                        # Remove commas from amount lines (starting with 'T')
                        if stripped.startswith('T'):
                            line = line.replace(',', '')

                        # Convert date format (lines starting with 'D')
                        elif stripped.startswith('D'):
                            date_value = stripped[1:]  # Remove the 'D' prefix
                            converted_date = self.convert_date_format(date_value)
                            line = f'D{converted_date}\n'

                        cleaned_data.append(line)

                    # Write cleaned data back to file
                    with open(file_path, 'w') as qif_file:
                        qif_file.writelines(cleaned_data)

                    # Now parse with PyQifParser
                    parser = PyQifParser(file_path)

                    # Call parse() method
                    parser.parse()

                    # Get transactions dataframe
                    transactions_df = parser.get_transactions()

                except Exception as e:
                    raise ValidationError(_("Wrong file format"))
                finally:
                    # Clean up temporary file
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)

                statement_list = []
                data_reference = []

                # Process parsed QIF data from the dataframe
                for index, row in transactions_df.iterrows():
                    # Access transaction fields from dataframe columns
                    date_entry = row['Date']
                    amount = row['Amount']
                    payee = row['Payee'] if pd.notna(row['Payee']) else ""
                    description = row['Description'] if pd.notna(
                        row['Description']) else ""
                    reference = row['Reference'] if pd.notna(
                        row['Reference']) else ""

                    # Validate required fields
                    if pd.isna(date_entry):
                        raise ValidationError(
                            _("Date is Missing in your uploaded sheet"))
                    if pd.isna(amount):
                        raise ValidationError(
                            _("Amount is Missing in your uploaded sheet"))
                    if not payee:
                        raise ValidationError(
                            _("Payee is Missing in your uploaded sheet"))

                    # Use description, reference, or generate from payee+date+amount as name
                    if description:
                        name = description
                    elif reference:
                        name = reference
                    else:
                        # Generate a unique name from payee, date, and amount
                        date_str = date_entry.strftime('%Y%m%d') if isinstance(
                            date_entry, pd.Timestamp) else str(date_entry)
                        name = f"{payee}_{date_str}_{abs(float(amount))}"

                    # Convert amount to float
                    try:
                        amount = float(amount)
                    except (ValueError, TypeError):
                        raise ValidationError(
                            _(f"Invalid amount format: {amount}"))

                    # Convert date to required format
                    try:
                        if isinstance(date_entry, str):
                            date_object = datetime.strptime(date_entry,
                                                            '%d/%m/%Y')
                        else:
                            # date_entry is already a datetime object from pandas
                            date_object = date_entry
                        date = date_object.strftime('%Y-%m-%d')
                    except Exception as e:
                        raise ValidationError(
                            _(f"Invalid date format: {date_entry}"))

                    statement_list.append([payee, amount, date, name])
                    data_reference.append(name)

                # Creating record
                validation_on_duplication_in_file(data_reference, split_tup[1])
                self.action_ofx_or_qif(split_tup[1], statement_list)
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Statements',
                    'view_mode': 'tree',
                    'res_model': 'account.bank.statement',
                }
        else:
            raise ValidationError(_("Choose correct file"))

    def action_ofx_or_qif(self, file_type, statement_list, ofx_file=False):
        """
           Process OFX or QIF statement data and create records.
           Args:
               file_type (str): File type, either '.ofx' or '.qif'.
               statement_list (list): List of statement data.
               ofx_file (OfxFile): OFX file object (default is False).
           Raises:
               ValidationError: If duplicate keys are found or if there are
               errors during record creation."""
        if statement_list:
            duplicate_keys = []
            records_to_create = []
            for item in statement_list:
                field_names = ['partner', 'amount', 'date'] if file_type == '.ofx' else \
                    ['partner', 'amount', 'date', 'name']
                data_file = pd.DataFrame([item], columns=field_names)
                key_value = ofx_file.account.routing_number if (file_type == '.ofx') else data_file['name'].iloc[0]
                query = """SELECT name FROM account_bank_statement WHERE name = %s"""
                self.env.cr.execute(query, (key_value,))
                result = self.env.cr.fetchone()
                if result:
                    duplicate_keys.append(result)
                else:
                    records_to_create.append({
                        'name': key_value,
                        'line_ids': [
                            fields.Command.create({
                                'date': data_file['date'].iloc[0],
                                'payment_ref': f"""import/Bnk/{data_file['date']
                                .iloc[0].strftime('%Y-%m-%d')}/ofx file""" if file_type == '.ofx'
                                else f"""import/Bnk/{data_file['date'].iloc[0]}/qif file""",
                                'partner_id': self.env['res.partner'].search([
                                    ('name', '=', data_file['partner'].iloc[0])]).id,
                                'journal_id': self.journal_id.id,
                                'amount': data_file['amount'].iloc[0],
                            })]
                    })
            self.duplication_and_create_record(duplicate_keys, records_to_create)
