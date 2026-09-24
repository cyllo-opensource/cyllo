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


class TestProjectProject(TransactionCase):
    """Tests for the project.project extension in cyllo_project_base.

    Covers:
        - Presence and default value of the ``is_fsm`` Boolean field.
        - Setting ``is_fsm=True`` / ``is_fsm=False`` on create and write.
        - Independence of ``is_fsm`` between different project records.
        - Copy behaviour (``copy=True`` by default for Boolean fields).
        - Field metadata (string label, help text).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Project = cls.env['project.project']

    # ── field existence & metadata ────────────────────────────────────────────

    def test_is_fsm_field_exists(self):
        """project.project must expose an is_fsm field."""
        self.assertIn(
            'is_fsm',
            self.Project._fields,
            "project.project must have an is_fsm field added by cyllo_project_base.",
        )

    def test_is_fsm_field_is_boolean(self):
        """is_fsm must be a Boolean field."""
        from odoo import fields
        self.assertIsInstance(
            self.Project._fields['is_fsm'],
            fields.Boolean,
        )

    def test_is_fsm_field_string_label(self):
        """is_fsm string label must be 'Field Service'."""
        self.assertEqual(
            self.Project._fields['is_fsm'].string,
            'Field Service',
        )

    def test_is_fsm_field_has_help(self):
        """is_fsm must carry a non-empty help text."""
        self.assertTrue(
            self.Project._fields['is_fsm'].help,
            "is_fsm must have a non-empty help string.",
        )

    # ── default value ─────────────────────────────────────────────────────────

    def test_is_fsm_defaults_to_false(self):
        """A newly created project must have is_fsm=False by default."""
        project = self.Project.create({'name': 'Default FSM Project'})
        self.assertFalse(
            project.is_fsm,
            "is_fsm must default to False for new projects.",
        )

    # ── create ────────────────────────────────────────────────────────────────

    def test_create_project_with_is_fsm_true(self):
        """Creating a project with is_fsm=True must persist the value."""
        project = self.Project.create({
            'name': 'FSM Project',
            'is_fsm': True,
        })
        self.assertTrue(project.is_fsm)

    def test_create_project_with_is_fsm_false(self):
        """Creating a project with is_fsm=False must persist the value."""
        project = self.Project.create({
            'name': 'Non-FSM Project',
            'is_fsm': False,
        })
        self.assertFalse(project.is_fsm)

    # ── write ─────────────────────────────────────────────────────────────────

    def test_write_is_fsm_true_to_false(self):
        """Writing is_fsm=False on a previously enabled project must update correctly."""
        project = self.Project.create({'name': 'Toggle FSM Project', 'is_fsm': True})
        project.write({'is_fsm': False})
        self.assertFalse(project.is_fsm)

    def test_write_is_fsm_false_to_true(self):
        """Writing is_fsm=True on a default project must update correctly."""
        project = self.Project.create({'name': 'Enable FSM Project'})
        self.assertFalse(project.is_fsm)
        project.write({'is_fsm': True})
        self.assertTrue(project.is_fsm)

    # ── independence between records ──────────────────────────────────────────

    def test_is_fsm_independent_between_projects(self):
        """is_fsm on one project must not affect another project's value."""
        fsm_project = self.Project.create({'name': 'FSM Enabled', 'is_fsm': True})
        normal_project = self.Project.create({'name': 'Normal Project'})
        self.assertTrue(fsm_project.is_fsm)
        self.assertFalse(normal_project.is_fsm)

    # ── copy behaviour ────────────────────────────────────────────────────────

    def test_copy_preserves_is_fsm_true(self):
        """Duplicating an FSM-enabled project must copy is_fsm=True."""
        original = self.Project.create({'name': 'Original FSM', 'is_fsm': True})
        copy = original.copy()
        self.assertTrue(
            copy.is_fsm,
            "Copying an is_fsm=True project must produce a copy with is_fsm=True.",
        )

    def test_copy_preserves_is_fsm_false(self):
        """Duplicating a non-FSM project must copy is_fsm=False."""
        original = self.Project.create({'name': 'Original Normal'})
        copy = original.copy()
        self.assertFalse(
            copy.is_fsm,
            "Copying an is_fsm=False project must produce a copy with is_fsm=False.",
        )

    # ── persistence (re-read from DB) ─────────────────────────────────────────

    def test_is_fsm_persisted_in_database(self):
        """is_fsm=True must survive an env cache invalidation (re-read from DB)."""
        project = self.Project.create({'name': 'Persist FSM', 'is_fsm': True})
        self.Project.invalidate_model(['is_fsm'])
        project_reloaded = self.Project.browse(project.id)
        self.assertTrue(
            project_reloaded.is_fsm,
            "is_fsm=True must be stored persistently and readable after cache clear.",
        )

    # ── multiple projects bulk write ──────────────────────────────────────────

    def test_bulk_write_is_fsm(self):
        """Writing is_fsm on a recordset must update all records."""
        projects = self.Project.create([
            {'name': 'Bulk Project 1'},
            {'name': 'Bulk Project 2'},
            {'name': 'Bulk Project 3'},
        ])
        self.assertFalse(all(projects.mapped('is_fsm')))
        projects.write({'is_fsm': True})
        self.assertTrue(all(projects.mapped('is_fsm')))
