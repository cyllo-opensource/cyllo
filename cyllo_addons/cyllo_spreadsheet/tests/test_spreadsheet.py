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
import zipfile

from odoo.exceptions import UserError
from odoo.tests import common


def _build_xlsx_like_archive(files):
    """Return a base64 encoded zip archive holding the given {name: content}."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for filename, content in files.items():
            archive.writestr(filename, content)
    return base64.b64encode(stream.getvalue())


class TestSpreadsheet(common.TransactionCase):
    """Tests for the spreadsheet.sheet record and its conversion helpers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_group = cls.env.ref(
            'cyllo_spreadsheet.group_cyllo_spreadsheet_admin')

    # -------------------------------------------------------------------------
    # Record creation
    # -------------------------------------------------------------------------
    def test_default_name(self):
        """A sheet created without a name gets the default title."""
        sheet = self.env['spreadsheet.sheet'].create({})
        self.assertEqual(sheet.name, 'Spreadsheet Unnamed')

    def test_creator_gets_read_and_write_access(self):
        """The creator is linked to both the read and the write access lists."""
        # env.user is OdooBot, which is archived, so a x2many read would filter
        # it out; create the sheet as a regular active user instead.
        user = self.env['res.users'].create({
            'name': 'Spreadsheet Author',
            'login': 'spreadsheet_author',
            'groups_id': [(6, 0, [
                self.env.ref(
                    'cyllo_spreadsheet.group_cyllo_spreadsheet_write_user').id,
            ])],
        })
        sheet = self.env['spreadsheet.sheet'].with_user(user).create({
            'name': 'Budget',
        })
        self.assertIn(user, sheet.user_read_ids)
        self.assertIn(user, sheet.user_write_ids)

    def test_company_defaults_to_current_company(self):
        """A sheet belongs to the active company by default."""
        sheet = self.env['spreadsheet.sheet'].create({'name': 'Forecast'})
        self.assertEqual(sheet.company_id, self.env.company)

    # -------------------------------------------------------------------------
    # Binary <-> JSON conversion
    # -------------------------------------------------------------------------
    def test_json_to_binary_round_trip(self):
        """JSON encoded to binary decodes back to the same structure."""
        sheet = self.env['spreadsheet.sheet'].create({'name': 'Round Trip'})
        payload = {'sheets': [{'name': 'Sheet1', 'cells': {'A1': {'content': '1'}}}]}
        sheet.json_to_binary_content(payload)
        self.assertTrue(sheet.converted_binary_content)
        self.assertEqual(sheet.decode_to_json(), payload)

    def test_convert_binary_to_json_extracts_archive_members(self):
        """An uploaded archive is exploded into a {filename: content} mapping."""
        binary = _build_xlsx_like_archive({
            'xl/workbook.xml': '<workbook/>',
            'docProps/core.xml': '<coreProperties/>',
        })
        sheet = self.env['spreadsheet.sheet'].create({
            'name': 'Imported',
            'binary_content': binary,
        })
        sheet.convert_binary_to_json()
        self.assertEqual(sheet.sheet_json['xl/workbook.xml'], '<workbook/>')
        self.assertEqual(sheet.sheet_json['docProps/core.xml'],
                         '<coreProperties/>')

    def test_convert_binary_to_json_handles_binary_members(self):
        """Non UTF-8 archive members are kept as base64 payloads."""
        raw = b'\x89PNG\r\n\x1a\n\xff\xfe'
        binary = _build_xlsx_like_archive({'xl/media/image1.png': raw})
        sheet = self.env['spreadsheet.sheet'].create({
            'name': 'With Image',
            'binary_content': binary,
        })
        sheet.convert_binary_to_json()
        self.assertEqual(
            sheet.sheet_json['xl/media/image1.png'],
            base64.b64encode(raw).decode('UTF-8'),
        )

    def test_convert_binary_to_json_prefers_converted_content(self):
        """Once converted content exists it takes precedence over the upload."""
        sheet = self.env['spreadsheet.sheet'].create({'name': 'Converted'})
        payload = {'version': 2}
        sheet.json_to_binary_content(payload)
        sheet.convert_binary_to_json()
        self.assertEqual(sheet.sheet_json, payload)

    def test_empty_sheet_converts_to_empty_mapping(self):
        """A sheet without any content converts to an empty payload."""
        sheet = self.env['spreadsheet.sheet'].create({'name': 'Empty'})
        sheet.convert_binary_to_json()
        # fields.Json stores any falsy value as NULL and reads it back as False
        self.assertFalse(sheet.sheet_json)

    # -------------------------------------------------------------------------
    # Public entry points
    # -------------------------------------------------------------------------
    def test_action_upload_sheet(self):
        """Uploading returns the id of a sheet holding the uploaded payload."""
        binary = _build_xlsx_like_archive({'xl/workbook.xml': '<workbook/>'})
        sheet_id = self.env['spreadsheet.sheet'].action_upload_sheet(
            binary_content=binary, name='Uploaded Sheet')
        sheet = self.env['spreadsheet.sheet'].browse(sheet_id)
        self.assertTrue(sheet.exists())
        self.assertEqual(sheet.name, 'Uploaded Sheet')
        self.assertEqual(sheet.binary_content, binary)

    def test_action_upload_sheet_default_name(self):
        """An upload without a name falls back to the placeholder title."""
        sheet_id = self.env['spreadsheet.sheet'].action_upload_sheet(
            binary_content=_build_xlsx_like_archive({'a.xml': '<a/>'}))
        self.assertEqual(
            self.env['spreadsheet.sheet'].browse(sheet_id).name,
            'Sheet Unknown',
        )

    def test_update_sheet_persists_json(self):
        """Updating a sheet re-encodes the JSON into the converted binary."""
        sheet = self.env['spreadsheet.sheet'].create({'name': 'Editable'})
        payload = {'sheets': [{'name': 'Sheet1'}]}
        sheet.update_sheet(sheet_json=payload)
        self.assertEqual(sheet.decode_to_json(), payload)

    def test_get_spreadsheet_data_returns_record_and_access(self):
        """Reading a sheet returns its values together with the access level."""
        sheet = self.env['spreadsheet.sheet'].create({'name': 'Readable'})
        data, access_level = sheet.get_spreadsheet_data()
        self.assertEqual(data['id'], sheet.id)
        self.assertEqual(data['name'], 'Readable')
        self.assertTrue(access_level)

    # -------------------------------------------------------------------------
    # Access control
    # -------------------------------------------------------------------------
    def test_get_access_data_requires_admin_group(self):
        """A plain user cannot read the sharing information of a sheet."""
        user = self.env['res.users'].create({
            'name': 'Spreadsheet Viewer',
            'login': 'spreadsheet_viewer',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        sheet = self.env['spreadsheet.sheet'].create({'name': 'Shared'})
        with self.assertRaises(UserError):
            sheet.with_user(user).get_access_data()

    def test_admin_group_exists(self):
        """The module ships the spreadsheet administrator group."""
        self.assertTrue(self.admin_group)
        self.assertIn(self.env.ref('base.user_admin'), self.admin_group.users)
