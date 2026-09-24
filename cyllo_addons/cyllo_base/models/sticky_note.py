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

    @api.model
    def edit_note(self, args):
        """Edit an existing Sticky Note with the provided arguments"""
        note_id = args['id']
        records = self.env['sticky.note'].browse(note_id)
        records.write(args)
