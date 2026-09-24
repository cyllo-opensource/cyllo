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
from odoo.tests.common import TransactionCase


# All five Boolean fields added by cyllo_project_base on res.config.settings.
_MODULE_FIELDS = [
    ('module_cyllo_project_product',   'Task Products'),
    ('module_cyllo_budget_project',    'Add Projects from budget'),
    ('module_cyllo_project_planning',  'Allocate employees to tasks directly from Project'),
    ('module_cyllo_field_service_project', 'Field Service'),
    ('module_hr_expense',              'Add expenses from Projects'),
]


class TestResConfigSettings(TransactionCase):
    """Tests for the res.config.settings extension in cyllo_project_base.

    Covers:
        - Presence and type of every added Boolean field.
        - String labels match the manifest declarations.
        - Fields default to False on a fresh settings record.
        - Each field can be individually set to True and written back.
        - All fields can be set simultaneously.
        - Field values are independent of each other.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Settings = cls.env['res.config.settings']

    # ── helpers ───────────────────────────────────────────────────────────────

    def _new_settings(self, **kwargs):
        """Create a transient res.config.settings record."""
        return self.Settings.create(kwargs)

    # ── field existence & type ────────────────────────────────────────────────

    def test_all_module_fields_exist(self):
        """All five module_* Boolean fields must exist on res.config.settings."""
        for field_name, _ in _MODULE_FIELDS:
            self.assertIn(
                field_name,
                self.Settings._fields,
                f"res.config.settings must have field '{field_name}'.",
            )

    def test_all_module_fields_are_boolean(self):
        """Every added field must be a Boolean."""
        from odoo import fields
        for field_name, _ in _MODULE_FIELDS:
            self.assertIsInstance(
                self.Settings._fields[field_name],
                fields.Boolean,
                f"Field '{field_name}' must be a Boolean.",
            )

    def test_all_module_fields_string_labels(self):
        """String labels must match the values declared in the model."""
        expected = dict(_MODULE_FIELDS)
        for field_name, label in expected.items():
            actual = self.Settings._fields[field_name].string
            self.assertEqual(
                actual,
                label,
                f"Field '{field_name}' string must be '{label}', got '{actual}'.",
            )

    # ── default values ────────────────────────────────────────────────────────

    def test_all_module_fields_default_false(self):
        """All added fields must default to False on a new settings record."""
        settings = self._new_settings()
        for field_name, _ in _MODULE_FIELDS:
            self.assertFalse(
                getattr(settings, field_name),
                f"Field '{field_name}' must default to False.",
            )

    # ── individual field writes ───────────────────────────────────────────────

    def test_module_cyllo_project_product_can_be_set_true(self):
        """module_cyllo_project_product can be set to True."""
        settings = self._new_settings(module_cyllo_project_product=True)
        self.assertTrue(settings.module_cyllo_project_product)

    def test_module_cyllo_budget_project_can_be_set_true(self):
        """module_cyllo_budget_project can be set to True."""
        settings = self._new_settings(module_cyllo_budget_project=True)
        self.assertTrue(settings.module_cyllo_budget_project)

    def test_module_cyllo_project_planning_can_be_set_true(self):
        """module_cyllo_project_planning can be set to True."""
        settings = self._new_settings(module_cyllo_project_planning=True)
        self.assertTrue(settings.module_cyllo_project_planning)

    def test_module_cyllo_field_service_project_can_be_set_true(self):
        """module_cyllo_field_service_project can be set to True."""
        settings = self._new_settings(module_cyllo_field_service_project=True)
        self.assertTrue(settings.module_cyllo_field_service_project)

    def test_module_hr_expense_can_be_set_true(self):
        """module_hr_expense can be set to True."""
        settings = self._new_settings(module_hr_expense=True)
        self.assertTrue(settings.module_hr_expense)

    # ── all fields simultaneously ─────────────────────────────────────────────

    def test_all_module_fields_can_be_set_true_simultaneously(self):
        """All five module fields can be set to True at the same time."""
        settings = self._new_settings(**{f: True for f, _ in _MODULE_FIELDS})
        for field_name, _ in _MODULE_FIELDS:
            self.assertTrue(
                getattr(settings, field_name),
                f"Field '{field_name}' must be True when all flags are enabled.",
            )

    # ── independence between fields ───────────────────────────────────────────

    def test_enabling_one_field_does_not_affect_others(self):
        """Setting one module flag to True must leave the others False."""
        for enabled_field, _ in _MODULE_FIELDS:
            settings = self._new_settings(**{enabled_field: True})
            for other_field, _ in _MODULE_FIELDS:
                if other_field == enabled_field:
                    self.assertTrue(getattr(settings, other_field))
                else:
                    self.assertFalse(
                        getattr(settings, other_field),
                        f"Enabling '{enabled_field}' must not affect '{other_field}'.",
                    )

    # ── write after create ────────────────────────────────────────────────────

    def test_write_module_field_from_false_to_true(self):
        """Writing a module field to True after creation must update correctly."""
        settings = self._new_settings()
        self.assertFalse(settings.module_cyllo_project_product)
        settings.write({'module_cyllo_project_product': True})
        self.assertTrue(settings.module_cyllo_project_product)

    def test_write_module_field_from_true_to_false(self):
        """Writing a module field back to False must update correctly."""
        settings = self._new_settings(module_cyllo_project_product=True)
        settings.write({'module_cyllo_project_product': False})
        self.assertFalse(settings.module_cyllo_project_product)
