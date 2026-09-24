# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from .common import ShopfloorCommon


class TestMrpBom(ShopfloorCommon):
    """Tests for the is_automated field added by cyllo_shopfloor on mrp.bom."""

    def test_is_automated_default_false(self):
        """Newly created BOM must default is_automated to False."""
        self.assertFalse(
            self.bom.is_automated,
            "BOM is_automated should be False by default."
        )

    def test_is_automated_can_be_set_true(self):
        """is_automated can be explicitly set to True on a BOM."""
        self.bom.is_automated = True
        self.bom.flush_recordset()
        self.assertTrue(self.bom.is_automated, "BOM is_automated should be True after writing.")

    def test_is_automated_toggle(self):
        """is_automated can be toggled back to False after being set True."""
        self.bom.is_automated = True
        self.bom.is_automated = False
        self.assertFalse(self.bom.is_automated, "BOM is_automated should revert to False.")

    def test_is_automated_propagates_to_mo(self):
        """Confirming an MO whose BOM has is_automated=True must set MO.is_automated=True."""
        self.bom.is_automated = True
        mo = self._make_mo(confirm=True)
        self.assertTrue(mo.is_automated, "MO.is_automated should mirror bom.is_automated on creation.")

    def test_is_automated_false_bom_gives_false_mo(self):
        """Confirming an MO whose BOM has is_automated=False must leave MO.is_automated=False."""
        self.bom.is_automated = False
        mo = self._make_mo(confirm=True)
        self.assertFalse(mo.is_automated, "MO.is_automated should be False when BOM is not automated.")
