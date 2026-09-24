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

class TestProjectMetrics(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # Set up Scope Data
        cls.carbon_scope = cls.env['carbon.scope'].create({
            'name': 'Scope 1', 
            'code': 'SCOPE1_proj', 
            'description': 'Direct Emissions'
        })
        # Set up Projects
        cls.project_water = cls.env['project.project'].create({
            'name': 'Water Conservation Facility',
            'company_id': cls.company.id,
        })
        cls.project_green = cls.env['project.project'].create({
            'name': 'Green Energy Initiative',
            'company_id': cls.company.id,
        })
        cls.project_standard = cls.env['project.project'].create({
            'name': 'Standard IT Implementation',
            'company_id': cls.company.id,
        })

    def test_01_water_project_compute(self):
        """Test that tasks in a 'Water' project have is_water_project set to True."""
        task = self.env['project.task'].create({
            'name': 'Install flow meters',
            'project_id': self.project_water.id,
            'recycled_water': 1500.0,
            'scope_id': self.carbon_scope.id,
        })
        self.assertTrue(task.is_water_project, "Task should be identified as a water project.")
        self.assertFalse(task.is_green_project, "Task should not be a green project.")
        self.assertEqual(task.recycled_water, 1500.0)

    def test_02_green_project_compute(self):
        """Test that tasks in a 'Green' project have is_green_project set to True."""
        task = self.env['project.task'].create({
            'name': 'Install Solar Panels',
            'project_id': self.project_green.id,
            'reduced_emissions': 500.5,
            'scope_id': self.carbon_scope.id,
        })
        self.assertFalse(task.is_water_project, "Task should not be a water project.")
        self.assertTrue(task.is_green_project, "Task should be identified as a green project.")
        self.assertEqual(task.reduced_emissions, 500.5)

    def test_03_standard_project_compute(self):
        """Test that tasks in a standard project are neither green nor water."""
        task = self.env['project.task'].create({
            'name': 'Configure servers',
            'project_id': self.project_standard.id,
        })
        self.assertFalse(task.is_water_project, "Task should not be a water project.")
        self.assertFalse(task.is_green_project, "Task should not be a green project.")
