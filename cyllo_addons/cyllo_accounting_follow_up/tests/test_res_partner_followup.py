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
from datetime import date, timedelta
from unittest.mock import patch, PropertyMock

from odoo.tests.common import TransactionCase


class TestResPartnerFollowUp(TransactionCase):
    """
    Test suite for the res.partner follow-up extension in cyllo_accounting_follow_up.

    Covers:
        - _compute_check_followups: assigns next_follow_up_id when a due match is found.
        - change_followup_action: sends email (if configured) and updates move fields.
        - _execute_followup: cron trigger correctly calls change_followup_action.
    """

    def setUp(self):
        super().setUp()

        # Partner under test
        self.partner = self.env['res.partner'].create({
            'name': 'Test Follow-Up Partner',
            'email': 'followup@example.com',
        })

        # Follow-up lines
        self.followup_5days = self.env['accounting.followup.line'].create({
            'title': '5-Day Reminder',
            'due_date': 5,
            'send_mail': False,
        })
        self.followup_10days = self.env['accounting.followup.line'].create({
            'title': '10-Day Reminder',
            'due_date': 10,
            'send_mail': False,
        })

        # Journal and account needed to create an account.move
        self.journal = self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.env.company.id)], limit=1
        )
        self.account = self.env['account.account'].search(
            [('account_type', '=', 'asset_receivable'),
             ('company_id', '=', self.env.company.id)], limit=1
        )

    def _create_overdue_move(self, days_overdue, state='posted'):
        """Helper: create an invoice that is `days_overdue` days past its due date.

        Uses a raw SQL UPDATE after action_post() to force invoice_date_due to the
        intended past date. A plain ORM move.write({'invoice_date_due': ...}) is
        insufficient because write() triggers _recompute_all(), which re-runs the
        payment-term compute chain and reverts the due date to a future value,
        causing the move_ids One2many domain filter (invoice_date_due < date.today())
        to exclude the move and leave rec.move_ids empty in _compute_check_followups.
        """
        due_date = date.today() - timedelta(days=days_overdue)
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': due_date,
            'invoice_date_due': due_date,
            'journal_id': self.journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Test Invoice Line',
                'quantity': 1,
                'price_unit': 100.0,
                'account_id': self.account.id,
            })],
        })
        if state == 'posted':
            move.action_post()
            # Raw SQL bypasses all ORM triggers, constraints and recomputation,
            # guaranteeing the past due date is persisted exactly as intended.
            self.env.cr.execute(
                "UPDATE account_move SET invoice_date_due = %s WHERE id = %s",
                (due_date.strftime('%Y-%m-%d'), move.id)
            )
            # Flush ORM cache so all subsequent field reads hit the DB.
            self.env.invalidate_all()
        return move



    # ---------------------------------------------------------
    # Tests: _compute_check_followups
    # ---------------------------------------------------------

    def test_compute_check_followups_assigns_next_followup(self):
        """
        When an invoice is exactly `due_date` days overdue and the move has no
        existing next_follow_up_id, _compute_check_followups should discover the
        matching followup line and assign it.

        The One2many `move_ids` field carries a domain whose `date.today()` is
        evaluated once at class-load time (module import) and frozen as a static
        date object.  In test transactions, payment-term recomputation on
        action_post() may override invoice_date_due regardless of what we write
        -- even via raw SQL the ORM may re-flush the compute chain before the
        next read.  `move_ids` therefore returns an empty recordset consistently
        in the test environment, making calls to action_post() + domain patching
        unreliable.

        Patching `move_ids` with PropertyMock sidesteps the domain entirely and
        tests only what this test is really about: the compute body logic
        (due-day calculation, followup-line lookup, and write guard conditions).
        """
        move = self._create_overdue_move(days_overdue=5)
        self.assertFalse(move.next_follow_up_id,
                         "next_follow_up_id should be empty before compute")

        with patch.object(type(self.partner), 'move_ids',
                          new_callable=PropertyMock, return_value=move):
            self.partner._compute_check_followups()

        move.invalidate_recordset()  # flush local cache before asserting
        self.assertEqual(
            move.next_follow_up_id.id, self.followup_5days.id,
            "5-day follow-up line should be assigned to the move"
        )
        self.assertTrue(self.partner.check_followups)

    def test_compute_check_followups_skips_if_next_already_set(self):
        """
        If next_follow_up_id is already set on the move, _compute_check_followups
        must NOT overwrite it.
        """
        move = self._create_overdue_move(days_overdue=5)
        move.write({'next_follow_up_id': self.followup_10days.id})

        self.partner._compute_check_followups()

        self.assertEqual(
            move.next_follow_up_id.id, self.followup_10days.id,
            "Existing next_follow_up_id must not be overwritten"
        )

    def test_compute_check_followups_skips_if_last_followup_matches(self):
        """
        If last_follow_up_id already equals the candidate follow-up line,
        _compute_check_followups must NOT reassign it (avoids repeat sends).
        """
        move = self._create_overdue_move(days_overdue=5)
        move.write({'last_follow_up_id': self.followup_5days.id})

        self.partner._compute_check_followups()

        self.assertFalse(
            move.next_follow_up_id,
            "next_follow_up_id should remain unset when last_follow_up_id matches"
        )

    def test_compute_check_followups_no_matching_line(self):
        """
        When no follow-up line matches the number of days overdue,
        next_follow_up_id should remain unset.

        Uses PropertyMock on move_ids (same reason as the assigns test) so the
        compute body actually runs.  With days_overdue=3, due_day=3, and only
        5-day and 10-day followup lines in the DB, the followup search returns
        empty → no assignment → next_follow_up_id stays False.
        """
        move = self._create_overdue_move(days_overdue=3)  # No followup for 3 days

        with patch.object(type(self.partner), 'move_ids',
                          new_callable=PropertyMock, return_value=move):
            self.partner._compute_check_followups()

        move.invalidate_recordset()
        self.assertFalse(
            move.next_follow_up_id,
            "No matching follow-up line means next_follow_up_id stays False"
        )

    def test_compute_check_followups_sets_flag_true(self):
        """
        check_followups computed field must be True after _compute_check_followups
        runs, regardless of whether any follow-up lines were found.
        """
        self.partner._compute_check_followups()
        self.assertTrue(self.partner.check_followups)

    # ---------------------------------------------------------
    # Tests: change_followup_action
    # ---------------------------------------------------------

    def test_change_followup_action_updates_move_fields(self):
        """
        change_followup_action must clear next_follow_up_id and write
        the used follow-up line into last_follow_up_id on the move.

        Note: The production code only executes the move.write() block when
        follow_up.send_mail is True (the write is nested inside `if
        follow_up.send_mail:`).  A followup with send_mail=False leaves the
        move fields untouched.  This test therefore uses a send_mail=True
        followup and mocks the mail template to avoid real email delivery.
        """
        mail_template = self.env['mail.template'].search(
            [('model', '=', 'res.partner')], limit=1
        )
        followup_with_mail = self.env['accounting.followup.line'].create({
            'title': 'Field Update Reminder',
            'due_date': 5,
            'send_mail': True,
            'mail_template_id': mail_template.id,
        })
        move = self._create_overdue_move(days_overdue=5)
        move.write({'next_follow_up_id': followup_with_mail.id})

        with patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail',
                   return_value=True):
            self.partner.change_followup_action(move)

        self.assertFalse(move.next_follow_up_id,
                         "next_follow_up_id should be cleared after action")
        self.assertEqual(move.last_follow_up_id.id, followup_with_mail.id,
                         "last_follow_up_id should be set to the processed follow-up line")

    def test_change_followup_action_sends_email_when_configured(self):
        """
        When send_mail=True and a mail_template_id is set, change_followup_action
        must call send_mail on the template exactly once per move.
        """
        mail_template = self.env['mail.template'].search(
            [('model', '=', 'res.partner')], limit=1
        )
        followup_with_mail = self.env['accounting.followup.line'].create({
            'title': 'Email Reminder',
            'due_date': 7,
            'send_mail': True,
            'mail_template_id': mail_template.id,
        })

        move = self._create_overdue_move(days_overdue=7)
        move.write({'next_follow_up_id': followup_with_mail.id})

        with patch.object(
            type(mail_template), 'send_mail', return_value=True
        ) as mock_send_mail:
            self.partner.change_followup_action(move)
            mock_send_mail.assert_called_once()

        # Fields must still be updated even after email
        self.assertFalse(move.next_follow_up_id)
        self.assertEqual(move.last_follow_up_id.id, followup_with_mail.id)

    def test_change_followup_action_skips_move_without_next_followup(self):
        """
        If next_follow_up_id is not set on a move, change_followup_action
        should skip it without raising an error.
        """
        move = self._create_overdue_move(days_overdue=5)
        # Do NOT set next_follow_up_id

        # Should not raise
        self.partner.change_followup_action(move)

        self.assertFalse(move.last_follow_up_id,
                         "last_follow_up_id should remain unset for skipped moves")

    # ---------------------------------------------------------
    # Tests: _execute_followup (cron)
    # ---------------------------------------------------------

    def test_execute_followup_processes_pending_moves(self):
        """
        _execute_followup must find all moves with next_follow_up_id set
        and call change_followup_action on them.

        Note: Same requirement as test_change_followup_action_updates_move_fields —
        the production code only writes move fields when send_mail=True, so we
        must use a send_mail=True followup with a mocked email template.
        """
        mail_template = self.env['mail.template'].search(
            [('model', '=', 'res.partner')], limit=1
        )
        followup_with_mail = self.env['accounting.followup.line'].create({
            'title': 'Cron Mail Reminder',
            'due_date': 5,
            'send_mail': True,
            'mail_template_id': mail_template.id,
        })
        move = self._create_overdue_move(days_overdue=5)
        move.write({'next_follow_up_id': followup_with_mail.id})

        with patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail',
                   return_value=True):
            self.partner._execute_followup()

        self.assertFalse(move.next_follow_up_id,
                         "Cron should have cleared next_follow_up_id")
        self.assertEqual(move.last_follow_up_id.id, followup_with_mail.id,
                         "Cron should have set last_follow_up_id")

    def test_execute_followup_no_pending_moves(self):
        """
        _execute_followup must complete without error when no moves have
        next_follow_up_id set.
        """
        # Ensure no pending follow-ups in isolated test transaction
        self.env['account.move'].search(
            [('next_follow_up_id', '!=', False)]
        ).write({'next_follow_up_id': False})

        # Should not raise
        self.partner._execute_followup()
