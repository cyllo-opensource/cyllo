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
from .common import TestProjectProductBase


class TestProjectProject(TestProjectProductBase):
    """Tests for ProjectProject extensions added by cyllo_project_product."""

    # ------------------------------------------------------------------
    # Field defaults
    # ------------------------------------------------------------------

    def test_allow_task_products_default_false(self):
        """allow_task_products must default to False on new projects."""
        project = self.env['project.project'].create({'name': 'Defaults Check'})
        self.assertFalse(project.allow_task_products)

    def test_allow_extra_quotations_default_false(self):
        """allow_extra_quotations must default to False on new projects."""
        project = self.env['project.project'].create({'name': 'Defaults Check'})
        self.assertFalse(project.allow_extra_quotations)

    # ------------------------------------------------------------------
    # Field assignment
    # ------------------------------------------------------------------

    def test_enable_task_products(self):
        """Setting allow_task_products=True persists correctly."""
        self.project_plain.allow_task_products = True
        self.assertTrue(self.project_plain.allow_task_products)

    def test_enable_extra_quotations(self):
        """Setting allow_extra_quotations=True persists correctly."""
        self.project_plain.allow_extra_quotations = True
        self.assertTrue(self.project_plain.allow_extra_quotations)

    def test_both_flags_independent(self):
        """allow_task_products and allow_extra_quotations are independent flags."""
        project = self.env['project.project'].create({
            'name': 'Flag Independence',
            'allow_task_products': True,
            'allow_extra_quotations': False,
        })
        self.assertTrue(project.allow_task_products)
        self.assertFalse(project.allow_extra_quotations)

    def test_disable_then_reenable(self):
        """Toggling a flag off and back on works as expected."""
        self.project.allow_task_products = False
        self.assertFalse(self.project.allow_task_products)
        self.project.allow_task_products = True
        self.assertTrue(self.project.allow_task_products)
