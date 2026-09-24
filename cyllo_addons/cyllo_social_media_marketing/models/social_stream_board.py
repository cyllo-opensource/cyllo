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


class SocialStreamBoard(models.Model):
    """ A saved Hootsuite-style Streams board: a named set of columns, each one
    watching a connected account/stream type. Boards are private workspace
    layout, not shared business data - one user's boards are invisible to
    everyone else (enforced by social_stream_board_rule). """
    _name = "social.stream.board"
    _description = "Social Stream Board"
    _order = "sequence, id"

    name = fields.Char(required=True)
    user_id = fields.Many2one('res.users', string="Owner", required=True,
                              default=lambda self: self.env.user, index=True)
    company_id = fields.Many2one('res.company', string="Company",
                                 default=lambda self: self.env.company.id)
    sequence = fields.Integer(default=10)
    column_ids = fields.One2many('social.stream.column', 'board_id', string="Columns")
    active = fields.Boolean(default=True)

    @api.model
    def get_boards_with_columns(self):
        """ Everything the Streams screen needs in one round trip: this user's
        boards, each with its columns already expanded. """
        boards = self.search([('user_id', '=', self.env.user.id)])
        return [{
            'id': board.id,
            'name': board.name,
            'sequence': board.sequence,
            'columns': [column._to_dict() for column in board.column_ids
                       if column._account_is_connected()],
        } for board in boards]

    @api.model
    def action_create_board(self, name):
        max_sequence = max(self.search([('user_id', '=', self.env.user.id)]).mapped('sequence') or [0])
        board = self.create({'name': name, 'sequence': max_sequence + 10})
        return {
            'id': board.id,
            'name': board.name,
            'sequence': board.sequence,
            'columns': [],
        }

    @api.model
    def action_reorder_boards(self, ordered_ids):
        for index, board_id in enumerate(ordered_ids):
            self.browse(board_id).write({'sequence': (index + 1) * 10})
        return True
