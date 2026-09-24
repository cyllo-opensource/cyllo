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
import io
import json
import xlsxwriter
import zipfile

from odoo.http import Controller , content_disposition, request, route


class SpreadsheetController(Controller):

    @route('/spreadsheet/download', type='http', auth='user')
    def download_converted_binary_content(self, files, name):
        """
        This method handles the download of a ZIP-compressed XLSX file that
         contains multiple XML file parts.

        It expects a JSON-encoded string (`files`) containing a list of
        dictionaries, where each dictionary represents a file part with its
         content and path. The method will generate an in-memory ZIP file and
         return it as an XLSX file for download.

        :param files: A JSON-encoded string representing the file parts to be
         added to the ZIP file.
                      Each part should have 'path' (the file path in the ZIP)
                       and 'content' (the file's content).
        :param name: The desired filename for the XLSX file
        (without the file extension). If not provided or missing the
         ".xlsx" extension, it will be added automatically.
        :param kwargs: Additional keyword arguments passed to the route.
        :return: A response containing the generated XLSX file,
         prompting the user to download it.
        :raises: Returns a 404 error if any exception occurs during the process.
        """
        try:
            files = json.loads(files)
            binary_stream = io.BytesIO()
            with zipfile.ZipFile(binary_stream, 'w',
                                 zipfile.ZIP_DEFLATED) as zip_file:
                for file in files:
                    if 'content' in file:
                        zip_file.writestr(file['path'], file['content'])

            xlsx_content = binary_stream.getvalue()
            if not name.endswith('.xlsx'):
                name += '.xlsx'
            headers = [
                ('Content-Type',
                 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{name}"')
            ]
            return request.make_response(xlsx_content, headers=headers)
        except Exception as e:
            return request.not_found()

    @route('/spreadsheet/download/documents', type='http', auth='user', methods=['POST'], csrf=False)
    def download_documents_converted_binary_content(self, files=None, name=None):
        """
        This method is for downloading xlsx files from documents module
        """
        try:
            spreadsheet_data = json.loads(files)
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            for sheet in spreadsheet_data.get('sheets', []):
                worksheet = workbook.add_worksheet(sheet.get('name', 'Sheet1'))
                cells = sheet.get('cells', {})
                for cell_ref, cell_data in cells.items():
                    column_letter = ''.join(filter(str.isalpha, cell_ref))
                    row_number = int(''.join(filter(str.isdigit, cell_ref)))
                    column = self._column_letter_to_index(column_letter)
                    row = row_number - 1
                    worksheet.write(row, column, cell_data.get('content', ''))
            workbook.close()
            output.seek(0)
            xlsx_data = output.read()
            if not name.endswith('.xlsx'):
                name += '.xlsx'
            headers = [
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(name))
            ]
            return request.make_response(xlsx_data, headers=headers)

        except Exception as e:
            return request.not_found()

    def _column_letter_to_index(self, column):
        """Arranging the data in the cells """
        columns = column.upper()
        index = 0
        for column in columns:
            index = index * 26 + (ord(column) - ord('A') + 1)
        return index - 1
