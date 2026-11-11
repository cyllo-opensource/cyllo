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

import base64
from unittest.mock import MagicMock, patch
import requests
from odoo.addons.cyllo_issue_reporting.models.ir_http import \
    IrHttp as CylloIrHttp
from odoo.exceptions import AccessError, UserError
from odoo.tests import common
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestIssueReporting(common.TransactionCase):

    def setUp(self):
        super(TestIssueReporting, self).setUp()
        self.IssueReport = self.env['issue.report']
        self.ErrorReportWizard = self.env['error.report.wizard']
        self.PartnerTransferWizard = self.env['partner.transfer.wizard']
        self.ResUsers = self.env['res.users']
        self.ResCompany = self.env['res.company']

        # Setup Companies
        self.company_main = self.env.company
        self.company_secondary = self.ResCompany.create({
            'name': 'Secondary Test Company',
        })

        # Groups
        self.group_user = self.env.ref('cyllo_issue_reporting.group_error_reporting_user')
        self.group_manager = self.env.ref('cyllo_issue_reporting.group_error_reporting_manager')

        # Test Users
        self.user_reporter = self.ResUsers.create({
            'name': 'Reporter User',
            'login': 'reporter_user@test.com',
            'email': 'reporter_user@test.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.group_user.id])],
            'company_id': self.company_main.id,
            'company_ids': [(6, 0, [self.company_main.id])],
        })

        self.user_manager = self.ResUsers.create({
            'name': 'Issue Manager',
            'login': 'issue_manager@test.com',
            'email': 'issue_manager@test.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.group_manager.id])],
            'company_id': self.company_main.id,
            'company_ids': [(6, 0, [self.company_main.id])],
        })

        # Baseline Issue Report
        self.test_issue = self.IssueReport.create({
            'name': 'ZeroDivisionError: division by zero',
            'error_type': 'backend',
            'module_name': 'cyllo_custom_sales',
            'file_location': 'models/sale_order.py:120',
            'error_message': 'division by zero',
            'traceback': (
                'Traceback (most recent call last):\n'
                '  File "/odoo/addons/cyllo_custom_sales/models/sale_order.py", line 120, in action_confirm\n'
                '    res = 1 / 0\n'
                'ZeroDivisionError: division by zero'
            ),
            'url': 'https://cyllo.example.com/web#id=42&model=sale.order',
            'user_id': self.user_reporter.id,
            'company_id': self.company_main.id,
        })

    
    # 1. ISSUE REPORT MODEL TESTS
 
    def test_01_create_issue_report_sequence_and_defaults(self):
        """Test sequence generation from 'i_seq' and field defaults."""
        issue = self.IssueReport.create({
            'name': 'KeyError: context',
            'error_type': 'backend',
        })

        self.assertTrue(issue.issue_ref, "An issue reference should be generated.")
        self.assertNotEqual(issue.issue_ref, "New", "Default 'New' should be replaced by sequence.")
        self.assertTrue(issue.issue_ref.startswith('ISS/'), "Reference should start with ISS prefix.")
        self.assertEqual(issue.state, 'draft')
        self.assertEqual(issue.priority, '1')
        self.assertEqual(issue.company_id, self.env.company)

    def test_02_issue_report_state_transitions(self):
        """Test status transitions via action methods."""
        issue = self.test_issue

        # in_progress
        issue.action_set_in_progress()
        self.assertEqual(issue.state, 'in_progress')

        # resolved
        issue.action_set_resolved()
        self.assertEqual(issue.state, 'resolved')

        # cancelled
        issue.action_set_cancelled()
        self.assertEqual(issue.state, 'cancelled')

        # draft
        issue.action_set_draft()
        self.assertEqual(issue.state, 'draft')

    def test_03_action_partner_transfer(self):
        """Test opening the partner transfer wizard passes context correctly."""
        action = self.test_issue.action_partner_transfer()

        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'partner.transfer.wizard')
        self.assertEqual(action.get('target'), 'new')

        ctx = action.get('context', {})
        self.assertEqual(ctx.get('default_issue_report_id'), self.test_issue.id)
        self.assertEqual(ctx.get('default_name'), self.test_issue.name)
        self.assertEqual(ctx.get('default_error_type'), self.test_issue.error_type)
        self.assertEqual(ctx.get('default_issue_ref'), self.test_issue.issue_ref)

    def test_04_action_ticket_redirect(self):
        """Test redirecting to the partner ticket URL with validation."""
        issue = self.test_issue

        # When ticket_url is not set
        issue.ticket_url = False
        with self.assertRaises(UserError):
            issue.action_ticket_redirect()

        # When ticket_url is unsafe / invalid format
        issue.ticket_url = "javascript:alert(1)"
        with self.assertRaises(UserError):
            issue.action_ticket_redirect()

        # When valid
        issue.ticket_url = "https://accounts.cyllo.com/ticket/1001"
        action = issue.action_ticket_redirect()
        self.assertEqual(action.get('type'), 'ir.actions.act_url')
        self.assertEqual(action.get('url'), "https://accounts.cyllo.com/ticket/1001")
        self.assertEqual(action.get('target'), 'new')

    def test_05_action_login_redirect(self):
        """Test redirecting to the login URL with validation."""
        issue = self.test_issue

        # When login_redirect_url is not set
        issue.login_redirect_url = False
        with self.assertRaises(UserError):
            issue.action_login_redirect()

        # When unsafe
        issue.login_redirect_url = "ftp://invalid-scheme.com"
        with self.assertRaises(UserError):
            issue.action_login_redirect()

        # When valid
        issue.login_redirect_url = "https://accounts.cyllo.com/login"
        action = issue.action_login_redirect()
        self.assertEqual(action.get('type'), 'ir.actions.act_url')
        self.assertEqual(action.get('url'), "https://accounts.cyllo.com/login")
        self.assertEqual(action.get('target'), 'new')

    def test_06_web_read_group_cancelled_fold(self):
        """Test that the 'cancelled' column is folded by default in kanban group view."""
        # Ensure at least one cancelled issue exists
        self.test_issue.action_set_cancelled()

        result = self.IssueReport.web_read_group(
            domain=[],
            fields=['state'],
            groupby=['state'],
        )
        cancelled_groups = [g for g in result.get('groups', []) if g.get('state') == 'cancelled']
        if cancelled_groups:
            self.assertTrue(cancelled_groups[0].get('__fold'), "Cancelled column must be folded.")

    
    # 2. RES.USERS EXTENSION TESTS

    def test_07_res_users_issue_raised_count_and_action(self):
        """Test issue_raised_count computation and action_open_raised_issues window action."""
        self.assertEqual(self.user_reporter.issue_raised_count, 1)

        # Create another issue for the same user
        self.IssueReport.create({
            'name': 'ValueError: Invalid input',
            'user_id': self.user_reporter.id,
        })
        self.user_reporter._compute_issue_raised_count()
        self.assertEqual(self.user_reporter.issue_raised_count, 2)

        action = self.user_reporter.action_open_raised_issues()
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'issue.report')
        self.assertEqual(action.get('domain'), [('user_id', '=', self.user_reporter.id)])

 
    # 3. SETTINGS & IR.HTTP SESSION INFO TESTS
  
    def test_08_res_config_settings_and_session_info(self):
        """Test enabling issue reporting config and its propagation to session_info."""
       

        # 1. Test configuring via res.config.settings transient model
        settings = self.env['res.config.settings'].create({
            'is_issue_reporting': True,
        })
        settings.execute()
        self.assertTrue(
            bool(self.env['ir.config_parameter'].sudo().get_param('cyllo_issue_reporting.is_issue_reporting'))
        )

        # 2. Test session_info() injection without triggering web HTTP request stack
        mro = self.env['ir.http'].__class__.__mro__
        parent_cls = next(cls for cls in mro[mro.index(CylloIrHttp) + 1:] if 'session_info' in cls.__dict__)

        with patch.object(parent_cls, 'session_info', return_value={}):
            # Test when enabled
            session_data = self.env['ir.http'].session_info()
            self.assertTrue(session_data.get('is_issue_reporting'))

            # Test when disabled
            self.env['ir.config_parameter'].sudo().set_param('cyllo_issue_reporting.is_issue_reporting', '')
            session_data = self.env['ir.http'].session_info()
            self.assertFalse(session_data.get('is_issue_reporting'))

 
    # 4. ERROR REPORT WIZARD TESTS
   
    def test_09_error_report_wizard_traceback_parsing(self):
        """Test default_get of error.report.wizard correctly parses Python tracebacks."""
        sample_tb = (
            'Traceback (most recent call last):\n'
            '  File "/odoo/addons/base/models/ir_http.py", line 10, in _dispatch\n'
            '    return self._dispatch_hook()\n'
            '  File "/odoo/custom_addons/cyllo_billing/models/account_move.py", line 85, in action_post\n'
            '    raise ValueError("Posting failed")\n'
            'ValueError: Posting failed'
        )

        wizard_form = self.ErrorReportWizard.with_context(
            default_traceback=sample_tb,
            default_name='ValueError: Posting failed',
        ).new()

        vals = wizard_form.default_get(['module_name', 'file_location', 'error_type'])
        self.assertEqual(vals.get('error_type'), 'backend')
        self.assertEqual(vals.get('module_name'), 'cyllo_billing')
        self.assertIn('account_move.py', vals.get('file_location') or '')

    def test_10_error_report_wizard_action_send_report(self):
        """Test sending a report from error.report.wizard creates issue.report and notification."""
        file_content = base64.b64encode(b"Dummy screenshot content")
        wizard = self.ErrorReportWizard.create({
            'name': 'Client Error: Crash',
            'error_type': 'frontend',
            'module_name': 'cyllo_pos',
            'file_location': 'static/src/pos.js:55',
            'error_message': 'Cannot read properties of undefined',
            'traceback': 'TypeError: Cannot read properties of undefined\n    at pos.js:55',
            'user_notes': 'Happened on invoice printing',
            'attachment': file_content,
            'attachment_filename': 'screenshot.png',
        })

        action = wizard.action_send_report()
        self.assertEqual(action.get('tag'), 'issue_report_notification')

        issue_id = action.get('params', {}).get('issue_id')
        issue = self.IssueReport.browse(issue_id)
        self.assertTrue(issue.exists())
        self.assertEqual(issue.name, 'Client Error: Crash')
        self.assertEqual(issue.error_type, 'frontend')
        self.assertTrue(issue.is_readonly)

        # Verify attachment posted in chatter
        attached = self.env['ir.attachment'].search([
            ('res_model', '=', 'issue.report'),
            ('res_id', '=', issue.id),
        ])
        self.assertTrue(attached)
        self.assertEqual(attached.name, 'screenshot.png')

    # 5. PARTNER TRANSFER WIZARD TESTS

    def test_11_partner_transfer_wizard_default_get_attachment(self):
        """Test partner.transfer.wizard pulls existing attachment from issue report."""
        # Create attachment on issue report
        self.env['ir.attachment'].create({
            'name': 'crash_log.txt',
            'type': 'binary',
            'datas': base64.b64encode(b"Detailed error log"),
            'res_model': 'issue.report',
            'res_id': self.test_issue.id,
        })

        wizard_vals = self.PartnerTransferWizard.with_context(
            default_issue_report_id=self.test_issue.id,
        ).default_get(['attachment', 'attachment_filename'])

        self.assertTrue(wizard_vals.get('attachment'))
        self.assertEqual(wizard_vals.get('attachment_filename'), 'crash_log.txt')

    def test_12_partner_transfer_duplicate_prevention(self):
        """Test that transferring an already transferred issue raises UserError."""
        self.test_issue.state = 'transferred'

        wizard = self.PartnerTransferWizard.create({
            'issue_report_id': self.test_issue.id,
            'name': self.test_issue.name,
            'category_label': 'technical',
        })

        with self.assertRaises(UserError):
            wizard.action_send_report()

    @patch('requests.post')
    def test_13_partner_transfer_api_success(self, mock_post):
        """Test successful partner transfer via mocked API endpoint."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'jsonrpc': '2.0',
            'result': {
                'success': True,
                'ticket_id': 'TCK-9901',
                'redirect_url': 'https://accounts.cyllo.com/ticket/TCK-9901',
            }
        }
        mock_post.return_value = mock_response

        wizard = self.PartnerTransferWizard.create({
            'issue_report_id': self.test_issue.id,
            'name': self.test_issue.name,
            'error_type': self.test_issue.error_type,
            'issue_ref': self.test_issue.issue_ref,
            'module_name': self.test_issue.module_name,
            'file_location': self.test_issue.file_location,
            'error_message': self.test_issue.error_message,
            'category_label': 'technical',
        })

        action = wizard.action_send_report()

        # Verify state and ticket URL updated
        self.assertEqual(self.test_issue.state, 'transferred')
        self.assertEqual(self.test_issue.ticket_url, 'https://accounts.cyllo.com/ticket/TCK-9901')

        # Verify notification returned
        self.assertEqual(action.get('tag'), 'display_notification')
        self.assertEqual(action.get('params', {}).get('type'), 'success')

        # Verify chatter log
        messages = self.test_issue.message_ids
        self.assertTrue(any('TCK-9901' in (m.body or '') for m in messages))

    @patch('requests.post')
    def test_14_partner_transfer_api_failure_and_timeout(self, mock_post):
        """Test API failure and timeout exceptions during partner transfer."""
        wizard = self.PartnerTransferWizard.create({
            'issue_report_id': self.test_issue.id,
            'name': self.test_issue.name,
            'category_label': 'technical',
        })

        # Case A: API returns failure with login redirect
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'result': {
                'success': False,
                'error': 'Session expired',
                'redirect_url': 'https://accounts.cyllo.com/login',
            }
        }
        mock_post.return_value = mock_response

        action = wizard.action_send_report()
        self.assertEqual(action.get('params', {}).get('type'), 'danger')
        self.assertEqual(self.test_issue.login_redirect_url, 'https://accounts.cyllo.com/login')

        # Case B: Request Timeout
        mock_post.side_effect = requests.exceptions.Timeout()
        with self.assertRaises(UserError):
            wizard.action_send_report()

        # Case C: Connection Error
        mock_post.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaises(UserError):
            wizard.action_send_report()

  
    # 6. MULTI-COMPANY ISOLATION & ACCESS RIGHTS
   
    def test_15_multicompany_isolation(self):
        """Test multi-company record rule isolation on issue.report."""
        # Create an issue belonging to the secondary company
        secondary_issue = self.IssueReport.create({
            'name': 'Secondary Company Issue',
            'company_id': self.company_secondary.id,
        })

        # Reporter user belongs only to main company
        issues_seen = self.IssueReport.with_user(self.user_reporter).search([
            ('id', '=', secondary_issue.id)
        ])
        self.assertFalse(issues_seen, "User should not access issues from another company.")

    def test_16_access_rights(self):
        """Test access rights between regular users and issue reporting managers."""
        issue = self.test_issue

        # Regular user can read and update notes/status
        issue.with_user(self.user_reporter).read(['name', 'state'])
        issue.with_user(self.user_reporter).write({'user_notes': 'Updated comment'})

        # Regular user should not be able to unlink issue reports (perm_unlink=0)
        with self.assertRaises(AccessError):
            issue.with_user(self.user_reporter).unlink()

        # Manager can unlink issue reports (perm_unlink=1)
        issue.with_user(self.user_manager).unlink()
        self.assertFalse(issue.exists(), "Manager should be allowed to delete issue reports.")
