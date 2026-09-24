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
"""Tests for the AppointmentType (appointment.type) model extension in
cyllo_appointment_hr_recruitment.

Covers:
- ``category`` Selection field extension with the new 'interview' value.
- Creating appointment.type records with category='interview'.
- Searching for 'interview' category types.
- The ondelete='set default' behaviour when the selection entry is removed
  (module-level concern, validated via field metadata introspection).
"""

from odoo.tests.common import TransactionCase


class TestAppointmentType(TransactionCase):
    """Unit tests for appointment.type extensions added by
    cyllo_appointment_hr_recruitment."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.apt_type_interview = cls.env['appointment.type'].create({
            'name': 'HR Interview Session',
            'category': 'interview',
        })

    # category field extension
    def test_interview_category_is_valid_selection_value(self):
        """'interview' must be an accepted value for the category field."""
        field_def = self.env['appointment.type']._fields['category']
        valid_keys = [key for key, _label in field_def.selection]
        self.assertIn(
            'interview',
            valid_keys,
            "'interview' must be registered as a valid selection value for 'category'.",
        )

    def test_create_appointment_type_with_interview_category(self):
        """Creating an appointment.type with category='interview' must succeed."""
        self.assertEqual(
            self.apt_type_interview.category,
            'interview',
            "The stored category must be 'interview'.",
        )

    def test_interview_appointment_type_name_is_preserved(self):
        """Name of an interview appointment type must be stored correctly."""
        self.assertEqual(
            self.apt_type_interview.name,
            'HR Interview Session',
        )

    def test_search_by_interview_category_returns_record(self):
        """Searching appointment.type with category='interview' must return
        the created record."""
        found = self.env['appointment.type'].search([
            ('category', '=', 'interview'),
            ('name', '=', 'HR Interview Session'),
        ])
        self.assertIn(
            self.apt_type_interview,
            found,
            "Search by category='interview' must return the interview type.",
        )

    def test_multiple_interview_types_are_allowed(self):
        """Multiple appointment.type records with category='interview' are allowed."""
        second = self.env['appointment.type'].create({
            'name': 'Technical Interview Round',
            'category': 'interview',
        })
        found = self.env['appointment.type'].search([('category', '=', 'interview')])
        self.assertGreaterEqual(
            len(found), 2,
            "There should be at least two interview appointment types.",
        )
        self.assertIn(second, found)

    def test_interview_category_label_is_interview(self):
        """The display label for the 'interview' key must be 'Interview'."""
        field_def = self.env['appointment.type']._fields['category']
        label_map = dict(field_def.selection)
        self.assertEqual(
            label_map.get('interview'),
            'Interview',
            "The display label for 'interview' must be 'Interview'.",
        )

    def test_write_category_to_interview(self):
        """Changing an existing appointment type's category to 'interview' must succeed."""
        apt_type = self.env['appointment.type'].create({
            'name': 'Generic Appointment',
            'category': 'other',
        })
        apt_type.write({'category': 'interview'})
        self.assertEqual(
            apt_type.category,
            'interview',
            "Writing category='interview' to an existing record must persist.",
        )

    def test_write_category_from_interview_to_other(self):
        """Changing category away from 'interview' to a valid base value must succeed."""
        apt_type = self.env['appointment.type'].create({
            'name': 'Changeable Interview Type',
            'category': 'interview',
        })
        apt_type.write({'category': 'other'})
        self.assertEqual(
            apt_type.category,
            'other',
            "Changing category from 'interview' to 'other' must persist.",
        )

    def test_ondelete_metadata_is_set_default(self):
        """The ondelete strategy for the 'interview' selection value must be
        'set default' as declared in the model."""
        field_def = self.env['appointment.type']._fields['category']
        # The ondelete attribute is a dict mapping selection key -> strategy.
        ondelete = getattr(field_def, 'ondelete', {}) or {}
        self.assertEqual(
            ondelete.get('interview'),
            'set default',
            "ondelete for 'interview' must be 'set default'.",
        )

    def test_appointment_type_with_interview_category_unlink(self):
        """Deleting an interview appointment type must succeed without errors."""
        temp_type = self.env['appointment.type'].create({
            'name': 'Temporary Interview Type',
            'category': 'interview',
        })
        temp_id = temp_type.id
        temp_type.unlink()
        remaining = self.env['appointment.type'].search([('id', '=', temp_id)])
        self.assertFalse(
            remaining,
            "The appointment type must be deleted from the database.",
        )
