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
import json
import zipfile

from odoo import api, Command, fields, models
from odoo.exceptions import UserError


class Spreadsheet(models.Model):
    _name = 'spreadsheet.sheet'
    _description = 'Spreadsheet'
    _order = "id desc"

    image_1920 = fields.Image("Spreadsheet Thumbnail")
    name = fields.Char(default="Spreadsheet Unnamed")
    user_read_ids = fields.Many2many('res.users',
                                     'res_users_read_rel',
                                     string='Users Read',
                                     help="Record Read access for users")
    user_write_ids = fields.Many2many('res.users',
                                      'res_users_write_rel',
                                      string='Users Write',
                                      help="Record Write access for users")
    binary_content = fields.Binary(help="stores the original Binary files")
    converted_binary_content = fields.Binary(
        help="stores the updated Binary files")
    sheet_json = fields.Json(
        compute="_compute_sheet_json",
        store=False,
        readonly=True,
    )
    active = fields.Boolean(default=True),
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )

    @api.depends('binary_content')
    def _compute_sheet_json(self):
        """
        Compute method that automatically converts binary content to JSON
        when the `binary_content` field is updated.
        """
        self.convert_binary_to_json()

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['user_write_ids'] = [Command.link(self.env.user.id)]
            val['user_read_ids'] = [Command.link(self.env.user.id)]
        return super().create(vals_list)

    @api.model
    def action_upload_sheet(self, **kwargs):
        """
        Handles uploading a new spreadsheet. Extracts the necessary data,
         creates a record, and converts the binary content to JSON.
        :param kwargs: Input parameters such as binary content and name.
        :return: ID of the newly created spreadsheet record.
        """
        sheet_id = self.create(self._extract_sheet_data(**kwargs))
        sheet_id.convert_binary_to_json()
        return sheet_id.id

    def _extract_sheet_data(self, **kwargs):
        """
        Extracts and structures the data needed
         to create a new spreadsheet record.
        :param kwargs: Dictionary of input values (e.g., binary content, name).
        :return: Dictionary with structured data.
        """
        return {
            "binary_content": kwargs.get('binary_content'),
            "name": kwargs.get('name', "Sheet Unknown"),
        }

    def json_to_binary_content(self, json_data):
        """
        Converts JSON data to binary format and encodes it for storage.
        :param json_data: JSON representation of spreadsheet data.
        """
        self.converted_binary_content = base64.encodebytes(
            json.dumps(json_data).encode("UTF-8"))

    def convert_binary_to_json(self):
        """
        Converts the binary Excel content into a JSON structure compatible
         with the o-spreadsheet format.
        If `converted_binary_content` is already available, it decodes
         the binary content into JSON.
        Otherwise, it processes the raw `binary_content`
         (e.g., an uploaded Excel file).
        """
        if not self.converted_binary_content:
            extracted_data = {}
            if self.binary_content:
                decoded_binary = base64.decodebytes(self.binary_content)
                binary_stream = io.BytesIO(decoded_binary)
                with zipfile.ZipFile(binary_stream) as zip_data:
                    for file_info in zip_data.infolist():
                        try:
                            content = zip_data.read(file_info.filename).decode(
                                'UTF-8')
                        except UnicodeDecodeError:
                            content = base64.b64encode(
                                zip_data.read(file_info.filename)).decode(
                                'UTF-8')
                        except Exception as e:
                            raise UserError(
                                f"Error processing spreadsheet: {e}")
                        extracted_data[file_info.filename] = content
            self.sheet_json = extracted_data
        else:
            self.sheet_json = self.decode_to_json()

    def decode_to_json(self):
        """
        Decodes the `converted_binary_content` into JSON format.
       :return: Parsed JSON data.
       """
        decoded_binary = base64.b64decode(self.converted_binary_content)
        json_data = json.loads(decoded_binary.decode('utf-8'))
        return json_data

    def _get_write_values(self, **kwargs):
        """
        Prepares values for writing/updating the spreadsheet record.
        :param kwargs: Dictionary of fields and values to update.
        :return: Dictionary containing write values.
        """
        data = {
            "sheet_json": kwargs.get('sheet_json', "{}"),
        }
        if kwargs.get('image_1920'):
            data['image_1920'] = kwargs.get('image_1920')
        return data

    def get_spreadsheet_data(self):
        """
        Retrieves the spreadsheet data for the current record.
        :return: A dictionary representation of the record.
        """
        if self.ensure_one():
            access_level = self.user_access_level()
            return self.read()[0], access_level

    def update_sheet(self, **kwargs):
        """
        Updates the spreadsheet record with new values
        and re-encodes JSON data to binary if needed.
        :param kwargs: Fields and values to update (e.g., `sheet_json`).
        """
        self.write(self._get_write_values(**kwargs))
        if "sheet_json" in kwargs:
            sheet_json = kwargs.get("sheet_json", "{}")
            self.json_to_binary_content(sheet_json)

    def get_access_data(self):
        """
        Retrieves access information for the spreadsheet records.
        :return: A list of dictionaries containing record
         details and access information.
        """
        admin_group = self.env.ref(
            "cyllo_spreadsheet.group_cyllo_spreadsheet_admin")

        if not self.env.user.has_group(
                'cyllo_spreadsheet.group_cyllo_spreadsheet_admin'):
            raise UserError("You are not authorized to Share this spreadsheet.")
        data_structure = []

        admin_users = admin_group.users.ids
        for record in self:
            access_info = {}
            for user in record.user_write_ids:
                if user.id not in admin_users:
                    access_info[user.id] = {
                        "user": user.name,
                        "id": user.id,
                        "write": True,
                        "read": True,
                    }
            for user in record.user_read_ids:
                if user.id not in admin_users:
                    if user.id not in access_info:
                        access_info[user.id] = {
                            "user": user.name,
                            "id": user.id,
                            "write": False,
                            "read": True,
                        }
            data_structure.append({
                "id": record.id,
                "name": record.name,
                "access": list(access_info.values()),
            })
        return data_structure

    def apply_access_to_users(self, **kwargs):
        """
        Apply access levels to users for the given spreadsheet record.

        :param kwargs: A dictionary containing `access_level` and `users`.
        """
        user_ids = kwargs.get("users", [])
        access_level = kwargs.get("access_level", "viewer")

        if not user_ids:
            raise UserError("No users provided to apply access.")
        admin_group = self.env.ref(
            'cyllo_spreadsheet.group_cyllo_spreadsheet_admin')
        admin_users = admin_group.users.ids
        user_ids = [user_id for user_id in user_ids if
                    user_id not in admin_users]
        if not user_ids:
            raise UserError(
                "All provided users are admins and cannot be granted additional access.")
        group_id = self.env.ref(
            'cyllo_spreadsheet.group_cyllo_spreadsheet_write_user')
        linked_users = [Command.link(user_id) for user_id in user_ids]
        group_id.write({
            'users': linked_users,
        })
        for record in self:
            if access_level == "editor":
                record.user_write_ids = linked_users
                record.user_read_ids = linked_users
            elif access_level == "viewer":
                record.user_write_ids = [Command.unlink(user_id) for user_id in
                                         user_ids if
                                         user_id in record.user_write_ids.ids]
                record.user_read_ids = linked_users
            else:
                raise UserError("Invalid access level provided.")

    def toggle_access_level(self, user_id, access_level, is_add=False):
        """
        Toggle the access level (read/write) for a specific user on the
        spreadsheet record.
        - If `is_add` is True, the user is added to the access list.
        - If `is_add` is False, the user is removed from the access list.

        :param user_id: The ID of the user whose access level is being toggled.
        :param access_level: The type of access to toggle ('read' or 'write').
        :param is_add: If True, add the user to the access list. If False,
         remove the user.
        """
        if not user_id:
            raise UserError("No user specified to toggle access.")

        if access_level not in ["read", "write"]:
            raise UserError(
                "Invalid access level specified. Must be 'read' or 'write'.")
        write_group = self.env.ref(
            "cyllo_spreadsheet.group_cyllo_spreadsheet_write_user",
            raise_if_not_found=False)
        if write_group and user_id not in write_group.users.ids:
            write_group.users = [Command.link(user_id)]
        for record in self:
            if access_level == "write":
                if is_add:
                    if user_id not in record.user_write_ids.ids:
                        record.user_write_ids = [Command.link(user_id)]
                    if user_id not in record.user_read_ids.ids:
                        record.user_read_ids = [Command.link(user_id)]
                else:
                    if user_id in record.user_write_ids.ids:
                        record.user_write_ids = [Command.unlink(user_id)]
            elif access_level == "read":
                if is_add:
                    if user_id not in record.user_read_ids.ids:
                        record.user_read_ids = [Command.link(user_id)]
                else:
                    if user_id in record.user_read_ids.ids:
                        record.user_read_ids = [Command.unlink(user_id)]
                    if user_id in record.user_write_ids.ids:
                        record.user_write_ids = [Command.unlink(user_id)]

    def user_access_level(self):
        """
        Determine the user's access level and if they are an admin.
        :return: A dictionary with keys `is_admin` (bool) and
         `access` (str: 'read', 'write', or None)
        """
        self.ensure_one()
        user = self.env.user
        admin_group = self.env.ref(
            'cyllo_spreadsheet.group_cyllo_spreadsheet_admin',
            raise_if_not_found=False)
        is_admin = admin_group and user.id in admin_group.users.ids
        if is_admin:
            return {"is_admin": True,
                    "access": "write"}
        if user.id in self.user_write_ids.ids:
            access = "write"
        elif user.id in self.user_read_ids.ids:
            access = "read"
        else:
            access = False

        return {"is_admin": is_admin, "access": access}

    def share_sheet(self):
        return {
            'type': "ir.actions.client",
            'tag': 'share_to_user_spreadsheet',
        }

    def delete_sheet(self):
        self.unlink()
