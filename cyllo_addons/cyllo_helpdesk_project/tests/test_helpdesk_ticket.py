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
from odoo.tests.common import TransactionCase


class TestHelpdeskProject(TransactionCase):
    """Tests for cyllo_helpdesk_project — project/task bridge on
    helpdesk.ticket and project.task.

    Coverage:
    - Field existence on both models
    - use_project / project_id relay from helpdesk.team
    - _compute_task_count (zero, increment, decrement)
    - action_create_task context payload and message_post side-effect
    - action_view_tasks: list mode (0 tasks), list mode (many tasks),
      form shortcut (exactly 1 task)
    - project.task.helpdesk_ticket_id back-reference
    - Team with project disabled (use_project = False)
    - Ticket with no customer / no user / no project edge cases
    - ensure_one() guard on action methods (multi-record raise)
    - Unlinking tasks decrements count correctly
    - Task linked to a different ticket is not surfaced on this ticket
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Drop any billing_type NOT NULL added by optional modules ──────
        # Use a savepoint so a failure only rolls back this one DDL statement
        # and does not leave the whole transaction in an aborted state.
        cls.env.cr.execute("SAVEPOINT drop_billing_type_notnull")
        try:
            cls.env.cr.execute(
                "ALTER TABLE project_project "
                "ALTER COLUMN billing_type DROP NOT NULL"
            )
            cls.env.cr.execute("RELEASE SAVEPOINT drop_billing_type_notnull")
        except Exception:
            cls.env.cr.execute("ROLLBACK TO SAVEPOINT drop_billing_type_notnull")

        # ── Projects ─────────────────────────────────────────────────────
        cls.project = cls.env['project.project'].create({'name': 'HD Project'})
        cls.other_project = cls.env['project.project'].create({'name': 'Other Project'})

        # ── Teams ─────────────────────────────────────────────────────────
        cls.team = cls.env['helpdesk.team'].create({
            'name': 'Project Team',
            'use_project': True,
            'project_id': cls.project.id,
        })
        cls.team_no_project = cls.env['helpdesk.team'].create({
            'name': 'No-Project Team',
            'use_project': False,
        })

        # ── Partners ──────────────────────────────────────────────────────
        cls.partner = cls.env['res.partner'].create({
            'name': 'HD Customer',
            'email': 'hd_customer@test.com',
        })

        # ── Stage ─────────────────────────────────────────────────────────
        cls.stage = cls.env['helpdesk.stage'].search([], limit=1)
        if not cls.stage:
            cls.stage = cls.env['helpdesk.stage'].create({
                'name': 'New',
                'sequence': 1,
                'is_closed': False,
            })

        # ── Base ticket ───────────────────────────────────────────────────
        cls.ticket = cls.env['helpdesk.ticket'].create({
            'name': 'Base Test Ticket',
            'team_id': cls.team.id,
            'customer_id': cls.partner.id,
            'stage_id': cls.stage.id,
        })

    # ── Helpers ───────────────────────────────────────────────────────────

    def _make_task(self, ticket, name='Task', project=None):
        """Create a project.task linked to *ticket*."""
        return self.env['project.task'].create({
            'name': name,
            'helpdesk_ticket_id': ticket.id,
            'project_id': (project or self.project).id,
        })

    def _make_ticket(self, team=None, name='Ticket', customer=None):
        """Create an additional helpdesk.ticket for use in individual tests."""
        return self.env['helpdesk.ticket'].create({
            'name': name,
            'team_id': (team or self.team).id,
            'customer_id': (customer or self.partner).id,
            'stage_id': self.stage.id,
        })

    # ── Field existence ───────────────────────────────────────────────────

    def test_ticket_fields_exist(self):
        """All four new fields must be present on helpdesk.ticket."""
        ticket_fields = self.ticket._fields
        self.assertIn('use_project', ticket_fields)
        self.assertIn('project_id', ticket_fields)
        self.assertIn('task_ids', ticket_fields)
        self.assertIn('task_count', ticket_fields)

    def test_project_task_back_reference_field_exists(self):
        """helpdesk_ticket_id must be present on project.task."""
        self.assertIn('helpdesk_ticket_id', self.env['project.task']._fields)

    def test_team_fields_exist(self):
        """use_project and project_id must be present on helpdesk.team."""
        team_fields = self.team._fields
        self.assertIn('use_project', team_fields)
        self.assertIn('project_id', team_fields)

    # ── use_project / project_id relay ───────────────────────────────────

    def test_use_project_relayed_true(self):
        """use_project on ticket is True when team has use_project = True."""
        self.assertTrue(self.ticket.use_project)

    def test_project_id_relayed_from_team(self):
        """project_id on ticket equals the team's project_id."""
        self.assertEqual(self.ticket.project_id, self.project)

    def test_use_project_relayed_false(self):
        """use_project on ticket is False when team has use_project = False."""
        ticket = self._make_ticket(team=self.team_no_project, name='No-Proj Ticket')
        self.assertFalse(ticket.use_project)

    def test_project_id_empty_when_team_has_no_project(self):
        """project_id on ticket is empty when team carries no project."""
        ticket = self._make_ticket(team=self.team_no_project, name='No-Proj Ticket 2')
        self.assertFalse(ticket.project_id)

    def test_use_project_updates_on_team_change(self):
        """use_project re-evaluates when ticket.team_id is switched."""
        ticket = self._make_ticket(team=self.team, name='Switch Team Ticket')
        self.assertTrue(ticket.use_project)
        ticket.team_id = self.team_no_project
        self.assertFalse(
            ticket.use_project,
            "use_project must become False after team is switched to one without project.",
        )

    def test_project_id_updates_on_team_change(self):
        """project_id re-evaluates when ticket.team_id is switched."""
        ticket = self._make_ticket(team=self.team, name='Switch Team Project Ticket')
        self.assertEqual(ticket.project_id, self.project)
        ticket.team_id = self.team_no_project
        self.assertFalse(
            ticket.project_id,
            "project_id must clear after team is switched to one without a project.",
        )

    # ── _compute_task_count ───────────────────────────────────────────────

    def test_task_count_zero_initially(self):
        """task_count is 0 when no tasks are linked."""
        ticket = self._make_ticket(name='Zero Tasks Ticket')
        self.assertEqual(ticket.task_count, 0)

    def test_task_count_increments_on_task_creation(self):
        """task_count increments each time a task is linked."""
        ticket = self._make_ticket(name='Increment Ticket')
        self.assertEqual(ticket.task_count, 0)

        self._make_task(ticket, name='T1')
        self.assertEqual(ticket.task_count, 1)

        self._make_task(ticket, name='T2')
        self.assertEqual(ticket.task_count, 2)

        self._make_task(ticket, name='T3')
        self.assertEqual(ticket.task_count, 3)

    def test_task_count_decrements_on_task_unlink(self):
        """task_count decrements correctly when a task is deleted."""
        ticket = self._make_ticket(name='Decrement Ticket')
        t1 = self._make_task(ticket, name='Del T1')
        t2 = self._make_task(ticket, name='Del T2')
        self.assertEqual(ticket.task_count, 2)

        t1.unlink()
        self.assertEqual(ticket.task_count, 1)

        t2.unlink()
        self.assertEqual(ticket.task_count, 0)

    def test_task_count_isolated_per_ticket(self):
        """Tasks on one ticket do not affect task_count on another ticket."""
        ticket_a = self._make_ticket(name='Ticket A')
        ticket_b = self._make_ticket(name='Ticket B')

        self._make_task(ticket_a, name='Task for A')
        self._make_task(ticket_a, name='Task for A 2')

        self.assertEqual(ticket_a.task_count, 2)
        self.assertEqual(ticket_b.task_count, 0,
                         "Tasks linked to ticket_a must not count towards ticket_b.")

    def test_task_count_not_affected_by_unrelated_task(self):
        """A task with a different helpdesk_ticket_id is not included."""
        ticket_a = self._make_ticket(name='Owner Ticket')
        ticket_b = self._make_ticket(name='Other Ticket')
        self._make_task(ticket_b, name='Unrelated Task')

        self.assertEqual(ticket_a.task_count, 0,
                         "Tasks belonging to ticket_b must not appear on ticket_a.")

    # ── project.task back-reference ───────────────────────────────────────

    def test_task_back_reference_set_correctly(self):
        """helpdesk_ticket_id on the created task points to the originating ticket."""
        ticket = self._make_ticket(name='Back-ref Ticket')
        task = self._make_task(ticket, name='Back-ref Task')
        self.assertEqual(
            task.helpdesk_ticket_id,
            ticket,
            "task.helpdesk_ticket_id must point back to the ticket it was created from.",
        )

    def test_task_back_reference_clearable(self):
        """helpdesk_ticket_id can be cleared without error."""
        ticket = self._make_ticket(name='Clear Ref Ticket')
        task = self._make_task(ticket, name='Clear Ref Task')
        task.helpdesk_ticket_id = False
        self.assertFalse(task.helpdesk_ticket_id)
        self.assertEqual(ticket.task_count, 0,
                         "task_count should drop to 0 after the back-reference is cleared.")

    # ── action_create_task ────────────────────────────────────────────────

    def test_action_create_task_returns_window_action(self):
        """action_create_task must return a valid ir.actions.act_window dict."""
        action = self.ticket.action_create_task()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'project.task')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')

    def test_action_create_task_default_name(self):
        """action_create_task sets default_name to the ticket's subject."""
        action = self.ticket.action_create_task()
        self.assertEqual(action['context']['default_name'], self.ticket.name)

    def test_action_create_task_default_ticket_id(self):
        """action_create_task sets default_helpdesk_ticket_id to the ticket's id."""
        action = self.ticket.action_create_task()
        self.assertEqual(
            action['context']['default_helpdesk_ticket_id'], self.ticket.id)

    def test_action_create_task_default_project_id(self):
        """action_create_task sets default_project_id from ticket.project_id."""
        action = self.ticket.action_create_task()
        self.assertEqual(
            action['context']['default_project_id'], self.project.id)

    def test_action_create_task_default_partner_id(self):
        """action_create_task sets default_partner_id from ticket.customer_id."""
        action = self.ticket.action_create_task()
        self.assertEqual(
            action['context']['default_partner_id'], self.partner.id)

    def test_action_create_task_default_user_ids(self):
        """action_create_task includes the assigned agent in default_user_ids."""
        ticket = self._make_ticket(name='Agent Ticket')
        ticket.user_id = self.env.user
        action = ticket.action_create_task()
        self.assertIn(self.env.user.id, action['context']['default_user_ids'])

    def test_action_create_task_user_ids_empty_when_no_agent(self):
        """action_create_task sets default_user_ids to [] when no agent assigned."""
        ticket = self._make_ticket(name='No Agent Ticket')
        ticket.user_id = False
        action = ticket.action_create_task()
        self.assertEqual(action['context']['default_user_ids'], [])

    def test_action_create_task_project_id_false_when_no_project(self):
        """action_create_task sets default_project_id to False when no project."""
        ticket = self._make_ticket(
            team=self.team_no_project, name='No Project Ticket')
        action = ticket.action_create_task()
        self.assertFalse(action['context']['default_project_id'])

    def test_action_create_task_partner_id_false_when_no_customer(self):
        """action_create_task sets default_partner_id to False when no customer."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'No Customer Ticket',
            'team_id': self.team.id,
            'stage_id': self.stage.id,
        })
        action = ticket.action_create_task()
        self.assertFalse(action['context']['default_partner_id'])

    def test_action_create_task_posts_message(self):
        """action_create_task must post a chatter message on the ticket."""
        ticket = self._make_ticket(name='Msg Ticket')
        msg_before = self.env['mail.message'].search_count(
            [('res_id', '=', ticket.id), ('model', '=', 'helpdesk.ticket')])
        ticket.action_create_task()
        msg_after = self.env['mail.message'].search_count(
            [('res_id', '=', ticket.id), ('model', '=', 'helpdesk.ticket')])
        self.assertGreater(
            msg_after, msg_before,
            "action_create_task must post at least one chatter message.",
        )

    def test_action_create_task_ensure_one_raises_on_multi(self):
        """action_create_task must raise when called on a recordset of >1 ticket."""
        ticket_a = self._make_ticket(name='Multi A')
        ticket_b = self._make_ticket(name='Multi B')
        multi = ticket_a | ticket_b
        with self.assertRaises(ValueError):
            multi.action_create_task()

    # ── action_view_tasks ─────────────────────────────────────────────────

    def test_action_view_tasks_domain_filters_by_ticket(self):
        """action_view_tasks domain restricts tasks to the calling ticket."""
        ticket = self._make_ticket(name='Domain Ticket')
        self._make_task(ticket, name='Domain Task 1')
        self._make_task(ticket, name='Domain Task 2')
        action = ticket.action_view_tasks()
        self.assertIn(('helpdesk_ticket_id', '=', ticket.id), action['domain'])

    def test_action_view_tasks_list_mode_when_multiple_tasks(self):
        """action_view_tasks uses list,form view_mode when task_count > 1."""
        ticket = self._make_ticket(name='Multi Task Ticket')
        self._make_task(ticket, name='Multi T1')
        self._make_task(ticket, name='Multi T2')
        action = ticket.action_view_tasks()
        self.assertEqual(action['view_mode'], 'list,form')

    def test_action_view_tasks_form_shortcut_when_single_task(self):
        """action_view_tasks switches to form view and sets res_id for exactly 1 task."""
        ticket = self._make_ticket(name='Single Task Ticket')
        task = self._make_task(ticket, name='Single Task')
        action = ticket.action_view_tasks()
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['res_id'], task.id)

    def test_action_view_tasks_list_mode_when_zero_tasks(self):
        """action_view_tasks falls back to list,form when task_count is 0."""
        ticket = self._make_ticket(name='Empty Task Ticket')
        action = ticket.action_view_tasks()
        self.assertEqual(action['view_mode'], 'list,form',
                         "With 0 tasks the view should remain list,form (no shortcut).")

    def test_action_view_tasks_res_model(self):
        """action_view_tasks always targets project.task."""
        ticket = self._make_ticket(name='Model Check Ticket')
        action = ticket.action_view_tasks()
        self.assertEqual(action['res_model'], 'project.task')

    def test_action_view_tasks_default_context_ticket_id(self):
        """action_view_tasks carries default_helpdesk_ticket_id in context."""
        ticket = self._make_ticket(name='Context Ticket')
        action = ticket.action_view_tasks()
        self.assertEqual(
            action['context']['default_helpdesk_ticket_id'], ticket.id)

    def test_action_view_tasks_default_context_project_id(self):
        """action_view_tasks carries default_project_id in context."""
        ticket = self._make_ticket(name='Context Project Ticket')
        action = ticket.action_view_tasks()
        self.assertEqual(
            action['context']['default_project_id'], self.project.id)

    def test_action_view_tasks_ensure_one_raises_on_multi(self):
        """action_view_tasks must raise when called on a recordset of >1 ticket."""
        ticket_a = self._make_ticket(name='View Multi A')
        ticket_b = self._make_ticket(name='View Multi B')
        multi = ticket_a | ticket_b
        with self.assertRaises(ValueError):
            multi.action_view_tasks()

    # ── task_ids One2many integrity ───────────────────────────────────────

    def test_task_ids_reflects_linked_tasks(self):
        """task_ids recordset contains exactly the tasks linked to the ticket."""
        ticket = self._make_ticket(name='O2m Integrity Ticket')
        t1 = self._make_task(ticket, name='O2m T1')
        t2 = self._make_task(ticket, name='O2m T2')
        self.assertIn(t1, ticket.task_ids)
        self.assertIn(t2, ticket.task_ids)
        self.assertEqual(len(ticket.task_ids), 2)

    def test_task_ids_does_not_include_tasks_of_other_tickets(self):
        """task_ids must not leak tasks from a different ticket."""
        ticket_own = self._make_ticket(name='Own Ticket')
        ticket_other = self._make_ticket(name='Other O2m Ticket')
        own_task = self._make_task(ticket_own, name='Own Task')
        other_task = self._make_task(ticket_other, name='Other Task')
        self.assertIn(own_task, ticket_own.task_ids)
        self.assertNotIn(other_task, ticket_own.task_ids)
