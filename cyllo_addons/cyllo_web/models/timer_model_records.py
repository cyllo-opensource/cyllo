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


class TimerModelRecords(models.Model):
    """
    Model to store timer widget-related records.

    This model is used to track and manage the timer-related data for specific records.
    """
    _name = 'timer.model.records'
    _description = 'Timer Widget Records'

    model_id = fields.Char(help="Storing timer widget field records model")
    field_id = fields.Char(help="Storing timer widget field records")
    record_id = fields.Integer(help="Current model record id")
    start_timer = fields.Char(help="Widget start time")
    stopped_timer = fields.Boolean(
        help="Indicates if the timer for this record has been stopped",
        default=False)

    @api.model
    def timer_update(self, records):
        """
        Update the timer-related records.

        If an existing record is found, it updates the 'start_timer' and 'stopped_timer' fields.
        If no existing record is found, it creates a new record.

        Args:
            records (dict): A dictionary containing the model_id, field_id, record_id, start_timer, and stopped_timer.

        Returns:
            record (odoo.models.Model): The updated or created record.
        """
        existing = self.search([
            ('model_id', '=', records['model_id']),
            ('field_id', '=', records['field_id']),
            ('record_id', '=', records['record_id'])
        ])

        if existing:
            existing.write({
                'start_timer': records['start_timer'],
                'stopped_timer': records['stopped_timer']
            })
        else:
            record = self.create({
                'model_id': records['model_id'],
                'field_id': records['field_id'],
                'record_id': records['record_id'],
                'start_timer': records['start_timer'],
                'stopped_timer': records['stopped_timer']
            })
            return record

    @api.model
    def timer_stopped(self, records):
        """
        Update the 'stopped_timer' field of the timer-related records.

        Args:
            records (dict): A dictionary containing the model_id, field_id, record_id, and stopped_timer.
        """
        existing = self.search([
            ('model_id', '=', records['model_id']),
            ('field_id', '=', records['field_id']),
            ('record_id', '=', records['record_id'])
        ])

        if existing:
            existing.write({
                'stopped_timer': records['stopped_timer']
            })
