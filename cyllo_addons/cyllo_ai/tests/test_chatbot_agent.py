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

class TestChatbotAgent(TransactionCase):
    """
    Test cases for the 'chatbot.tools' model, focusing on table normalization,
    schema helpers, and the typed CRUD execution path (`_execute_plan`).
    """

    def setUp(self):
        """
        Setup test environment for chatbot tool tests.
        """
        super(TestChatbotAgent, self).setUp()
        self.ChatbotTools = self.env['chatbot.tools']

    def test_normalize_main_table(self):
        """
        Test the normalization of table names and aliases for SQL/ORM processing.
        """
        # String input
        res = self.ChatbotTools._normalize_main_table("res_partner")
        self.assertEqual(res, {"name": "res_partner", "alias": "res_partner"})

        # Dict input
        res_dict = self.ChatbotTools._normalize_main_table({"name": "sale_order", "alias": "so"})
        self.assertEqual(res_dict, {"name": "sale_order", "alias": "so"})

        # Dict partial
        res_partial = self.ChatbotTools._normalize_main_table({"table": "stock_picking"})
        self.assertEqual(res_partial["name"], "stock_picking")

    def test_execute_plan_create_and_audit(self):
        """A valid create op creates the record and writes one audit entry."""
        before = self.env['cyllo.ai.audit'].sudo().search_count([])
        res = self.ChatbotTools._execute_plan({
            "action": "create", "model": "res.partner",
            "values": {"name": "Cyllo Plan Test"},
        })
        self.assertNotIn("error", res, res)
        self.assertIn("id", res)
        partner = self.env['res.partner'].browse(res["id"])
        self.assertEqual(partner.name, "Cyllo Plan Test")
        after = self.env['cyllo.ai.audit'].sudo().search_count([])
        self.assertEqual(after, before + 1, "a create should log exactly one audit entry")

    def test_plan_inline_x2many_becomes_commands(self):
        """An x2many value (list of line objects) becomes (0,0,{...}) commands."""
        values = self.ChatbotTools._plan_build_values("res.partner", {
            "name": "Parent Co",
            "child_ids": [{"name": "Child Contact"}],
        })
        self.assertEqual(values["name"], "Parent Co")
        self.assertEqual(values["child_ids"], [(0, 0, {"name": "Child Contact"})])

    def test_plan_create_with_inline_x2many(self):
        """End to end: creating a record with x2many line objects persists them."""
        res = self.ChatbotTools._execute_plan({
            "action": "create", "model": "res.partner",
            "values": {"name": "Parent With Child",
                       "child_ids": [{"name": "Nested Child"}]},
        })
        self.assertNotIn("error", res, res)
        parent = self.env['res.partner'].browse(res["id"])
        self.assertEqual(parent.child_ids.mapped("name"), ["Nested Child"])

    def test_plan_resolves_m2o_by_name(self):
        """A many2one given as a NAME is resolved to its id via the comodel."""
        self.env['res.partner'].create({"name": "Acme Parent Co"})
        res = self.ChatbotTools._execute_plan({
            "action": "create", "model": "res.partner",
            "values": {"name": "Child Of Acme", "parent_id": "Acme Parent Co"},
        })
        self.assertNotIn("error", res, res)
        child = self.env['res.partner'].browse(res["id"])
        self.assertEqual(child.parent_id.name, "Acme Parent Co")

    def test_build_domain_accepts_dict_filter(self):
        """Filters work as both [field, op, value] triples and {field,operator,
        value} objects."""
        triple = self.ChatbotTools._plan_build_domain([["name", "=", "X"]])
        obj = self.ChatbotTools._plan_build_domain(
            [{"field": "name", "operator": "=", "value": "X"}])
        self.assertEqual(triple, [("name", "=", "X")])
        self.assertEqual(obj, [("name", "=", "X")])

    def test_write_records_read_runs_immediately(self):
        """A read action executes at once (no confirmation interrupt)."""
        res = self.ChatbotTools.write_records(
            "res.partner", "read", filters=[["id", "=", self.env.user.partner_id.id]])
        self.assertNotIn("__interrupt__", res)
        self.assertIn("result", res)

    def test_write_records_write_pauses_for_confirmation(self):
        """A write action returns an interrupt with the stored typed op."""
        res = self.ChatbotTools.write_records(
            "res.partner", "create", values={"name": "Pending Co"})
        self.assertTrue(res.get("__interrupt__"))
        self.assertIn("pending_query", res)
        # the recipient was not created yet
        self.assertFalse(self.env['res.partner'].search_count([("name", "=", "Pending Co")]))

    def test_execute_plan_rejects_unknown_model(self):
        """Unknown model returns a corrective error rather than executing."""
        res = self.ChatbotTools._execute_plan({"action": "read", "model": "no.such.model"})
        self.assertIn("error", res)

    def test_execute_plan_rejects_bad_action(self):
        """An unsupported action returns a corrective error."""
        res = self.ChatbotTools._execute_plan({"action": "drop", "model": "res.partner"})
        self.assertIn("error", res)

    def test_execute_plan_rejects_bad_operator(self):
        """A disallowed domain operator is rejected, not executed."""
        res = self.ChatbotTools._execute_plan({
            "action": "read", "model": "res.partner",
            "filters": [["name", "HACK", "x"]],
        })
        self.assertIn("error", res)

    def test_execute_plan_rejects_unknown_field(self):
        """An unknown field on a create is rejected."""
        res = self.ChatbotTools._execute_plan({
            "action": "create", "model": "res.partner",
            "values": {"not_a_field": "x"},
        })
        self.assertIn("error", res)

    def test_get_model_from_table(self):
        """
        Test resolving Odoo model names from database table names.
        """
        # Case 1: Existing model
        res = self.ChatbotTools._get_model_from_table(["res_partner"])
        self.assertEqual(res, ["res.partner"])

        # Case 2: Model name passed
        res_model = self.ChatbotTools._get_model_from_table(["res.users"])
        self.assertEqual(res_model, ["res.users"])

    def test_get_fields_for_models(self):
        """
        Test retrieving field metadata for a given list of Odoo models.
        """
        fields_map = self.ChatbotTools._get_fields_for_models(["res.partner"])
        self.assertIn("res.partner", fields_map)
        self.assertTrue(len(fields_map["res.partner"]) > 0)
        self.assertIn("name", fields_map["res.partner"])
