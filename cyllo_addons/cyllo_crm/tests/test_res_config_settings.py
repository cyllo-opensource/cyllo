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
from unittest.mock import patch, MagicMock


class TestResConfigSettings(TransactionCase):
    """
    Unit tests for the customizations in ResConfigSettings.

    This class ensures:
    - Onchange behavior for enabling/disabling the advance lead module.
    - Proper module uninstallation via post-commit hooks in set_values().
    - Correct wizard behavior when configuring exit criteria in CRM stage
    """
    @classmethod
    def setUpClass(cls):
        """
        Set up shared test data:
        - A company and res.config.settings record.
        - CRM stages and a mail activity type.
        - A crm.stage.activity marked as exit criteria.
        - A clean ResConfigSettings record for test usage.
        """
        super().setUpClass()

        cls.env.cr.execute("ALTER TABLE res_company ALTER COLUMN security_lead SET DEFAULT 0.0")
        cls.env.cr.execute("ALTER TABLE project_project ALTER COLUMN billing_type SET DEFAULT 'not_billable'")
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company',
        })
        cls.settings_model = cls.env['res.config.settings']
        cls.config = cls.env['res.config.settings'].create({
            'company_id': cls.company.id,
        })
        cls.satge1= cls.env['crm.stage'].create({'name': 'Stage1'})
        cls.satge2= cls.env['crm.stage'].create({'name': 'Stage2'})
        cls.user = cls.env.ref("base.user_admin")
        cls.activity_type = cls.env['mail.activity.type'].create({
            'name': 'Follow Up',
            'category': 'default',
        })

        cls.exit_activity = cls.env['crm.stage.activity'].create({
            'stage_id': cls.satge1.id,
            'activity_id': cls.activity_type.id,
            'user_id': cls.user.id,
            'is_exit_criteria': True,
        })
        cls.settings = cls.env['res.config.settings'].create({})

    def test_onchange_module_cyllo_crm_advance_lead(self):
        """
        Test that enabling/disabling the `module_cyllo_crm_advance_lead`
        field properly toggles the `group_use_lead` flag.
        """
        settings = self.settings_model.create({
            'module_cyllo_crm_advance_lead': True
        })
        settings._onchange_module_cyllo_crm_advance_lead()
        self.assertTrue(settings.group_use_lead)
        settings = self.settings_model.create({
            'module_cyllo_crm_advance_lead': False,
        })
        settings._onchange_module_cyllo_crm_advance_lead()
        self.assertFalse(settings.group_use_lead)

    def test_set_values(self):
        """
        Test the behavior of set_values():
        - If group_use_lead is False, uninstall modules via a postcommit hook.
        - If group_use_lead is True, ensure no uninstall actions are triggered.
        """
        settings = self.env['res.config.settings'].create({
            'group_use_lead': False,
        })

        fake_module = MagicMock()
        fake_module.button_immediate_uninstall = MagicMock()

        with patch.object(type(self.env['ir.module.module']), "search",
                          return_value=fake_module), \
                patch.object(type(self.env.cr.postcommit),
                             "add") as mock_postcommit_add:
            settings.set_values()
            self.assertEqual(
                type(self.env['ir.module.module']).search.call_count, 2)
            mock_postcommit_add.assert_called()
            uninstall_lambda = mock_postcommit_add.call_args[0][0]
            uninstall_lambda()
            fake_module.button_immediate_uninstall.assert_called_once()
        settings = self.env['res.config.settings'].create({
            'group_use_lead': True,
        })
        with patch.object(type(self.env['ir.module.module']),
                          "search") as mock_search, \
                patch.object(type(self.env.cr.postcommit),
                             "add") as mock_postcommit_add:
            settings.set_values()
            mock_search.assert_not_called()
            uninstall_calls = [
                c for c in mock_postcommit_add.call_args_list
                if "button_immediate_uninstall" in str(c)
            ]
            self.assertEqual(len(uninstall_calls), 0)

    def test_action_configure_exit_criteria(self):
        """
        Test the action_configure_exit_criteria method:
        - Wizard is created with all stages.
        - Existing exit criteria are loaded into the wizard.
        - Context correctly reflects whether exit criteria exist.
        """
        action = self.settings.action_configure_exit_criteria()
        self.assertEqual(action["res_model"], "crm.stage.exit.criteria")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["view_mode"], "form")
        wizard = self.env["crm.stage.exit.criteria"].browse(action["res_id"])
        self.assertIn(self.satge1.id, wizard.stage_ids.ids)
        self.assertIn(self.satge2.id, wizard.stage_ids.ids)
        self.assertTrue(wizard.exit_criteria_ids,
                        "Exit criteria should be loaded")
        exit_criteria_record = wizard.exit_criteria_ids[0]

        self.assertEqual(exit_criteria_record.stage_id.id,
                         self.exit_activity.stage_id.id)
        self.assertEqual(exit_criteria_record.activity_id.id,
                         self.exit_activity.activity_id.id)
        self.assertEqual(exit_criteria_record.user_id.id,
                         self.exit_activity.user_id.id)
        self.assertTrue(action["context"]["has_criteria"])
