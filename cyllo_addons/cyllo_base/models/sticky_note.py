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
from odoo import api, fields, models


class StickyNote(models.Model):
    """This class represents a Sticky Note model for storing note details"""
    _name = "sticky.note"
    _description = "Sticky Note"

    title = fields.Char(help="title of the note")
    description = fields.Char(help="description of the note")
    colour = fields.Char(help="color of the note", string="Color")
    create_date = fields.Datetime(string="Created Date",
                                  help="Create date of a note")
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company,
        help="Current Company")
    is_pinned = fields.Boolean(string="Pinned", default=False)
    pin_scope = fields.Selection(
        [('view', 'View'), ('record', 'Record')], string="Pin Scope",
        help="Whether this note is bound to a general view (e.g. a list "
             "or dashboard) or to one specific record's form view. Empty "
             "means the note is not context-bound and is always visible.")
    pinned_action_key = fields.Char(
        string="Pinned Action",
        help="Identifier (action id or client action tag) of the action "
             "this note is pinned to, used when pin_scope is 'view'")
    pinned_view_type = fields.Char(
        string="Pinned View Type",
        help="View type (list, kanban, dashboard, etc.) this note is "
             "pinned to, used when pin_scope is 'view'")
    pinned_res_model = fields.Char(
        string="Pinned Model",
        help="Model of the record this note is bound to, used when "
             "pin_scope is 'record'")
    pinned_res_id = fields.Integer(
        string="Pinned Record ID",
        help="ID of the record this note is bound to, used when "
             "pin_scope is 'record'")
    checklist = fields.Text(string="Checklist", help="JSON list of checklist items")
    drawing = fields.Text(string="Drawing Data", help="Base64 PNG image or canvas drawing data")
    images = fields.Text(string="Attached Images",
                          help="JSON list of images attached to the note, "
                               "each entry as {'name': <filename>, 'data': <base64 data URL>}")

    @api.model
    def edit_note(self, args):
        """Edit an existing Sticky Note with the provided arguments"""
        note_id = args['id']
        records = self.env['sticky.note'].browse(note_id)
        write_vals = {k: v for k, v in args.items() if k != 'id'}
        records.write(write_vals)
