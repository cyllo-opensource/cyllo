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
from odoo.tests import common
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class TestHelpdeskFeatures(common.TransactionCase):

    def setUp(self):
        super(TestHelpdeskFeatures, self).setUp()
        self.Team = self.env['helpdesk.team']
        self.Ticket = self.env['helpdesk.ticket']
        self.Partner = self.env['res.partner']
        self.Skill = self.env['helpdesk.skill']
        
        self.partner = self.Partner.create({'name': 'Test Customer'})
        self.team = self.Team.create({
            'name': 'Support Team',
            'assignment_method': 'skill',
        })
        self.skill_it = self.Skill.create({'name': 'IT'})
        
        self.user_tech = self.env['res.users'].create({
            'name': 'Tech User',
            'login': 'tech_user',
            'email': 'tech@example.com',
            'groups_id': [(6, 0, [self.env.ref('cyllo_helpdesk.cyllo_helpdesk_user').id])],
            'helpdesk_skill_ids': [(6, 0, [self.skill_it.id])]
        })

    def test_01_parent_child_linking(self):
        """ Test that closing a parent ticket closes its children """
        parent = self.Ticket.create({
            'name': 'Parent Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })
        child = self.Ticket.create({
            'name': 'Child Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
            'parent_id': parent.id,
        })
        
        solved_stage = self.env.ref('cyllo_helpdesk.solved_ticket')
        parent.stage_id = solved_stage.id
        parent.onchange_stage_id() # Trigger logic manually in test
        
        self.assertEqual(child.stage_id.id, solved_stage.id, "Child ticket should be solved when parent is solved")

    def test_02_ticket_dependencies(self):
        """ Test that a ticket cannot be closed if dependencies are unresolved """
        dep = self.Ticket.create({
            'name': 'Dependency',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })
        main_ticket = self.Ticket.create({
            'name': 'Main Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
            'dependency_ids': [(6, 0, [dep.id])]
        })
        
        solved_stage = self.env.ref('cyllo_helpdesk.solved_ticket')
        with self.assertRaises(UserError):
            main_ticket.stage_id = solved_stage.id
            main_ticket.onchange_stage_id()

    def test_03_skill_based_assignment(self):
        """ Test that tickets are assigned based on skills """
        ticket = self.Ticket.create({
            'name': 'IT Issue',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
            'skill_ids': [(6, 0, [self.skill_it.id])],
            'user_id': False, # Force assignment logic
        })
        # Note: creation triggers _assign_ticket
        self.assertEqual(ticket.user_id.id, self.user_tech.id, "Ticket should be assigned to the user with matching skill")

    def test_04_sla_pause(self):
        """ Test SLA pause toggle """
        ticket = self.Ticket.create({
            'name': 'SLA Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })
        ticket.action_toggle_sla_pause()
        self.assertTrue(ticket.sla_paused)
        self.assertTrue(ticket.sla_pause_date)
        
        ticket.action_toggle_sla_pause()
        self.assertFalse(ticket.sla_paused)

    def test_05_incoming_reply_posts_chatter_notice(self):
        """Test that incoming replies add an explicit chatter notice."""
        ticket = self.Ticket.create({
            'name': 'Reply Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })
        msg_dict = {
            'subject': 'Re: Reply Ticket',
            'body': (
                '<div>hellooooo</div>'
                '<div>On Fri, Sep 4, 2026 at 3:13 PM Nathan Bennet '
                '&lt;michealdicaprio0@gmail.com&gt; wrote:<br>'
                '<blockquote>hyyy</blockquote></div>'
            ),
        }
        ticket.message_update(msg_dict)

        notice = self.env['mail.message'].search([
            ('model', '=', 'helpdesk.ticket'),
            ('res_id', '=', ticket.id),
            ('body', 'ilike', 'A reply has been received and linked to this record.'),
        ])
        self.assertTrue(notice, "Incoming reply should post a chatter notice")
        self.assertIn('hellooooo', msg_dict['body'])
        self.assertIn('On Fri', msg_dict['body'])
        self.assertIn('hyyy', msg_dict['body'])

    def test_06_incoming_reply_preserves_original_body(self):
        """Inbound reply content is left for Cyllo's mail renderer to display."""
        ticket = self.Ticket.create({
            'name': 'Escaped Reply Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })
        msg_dict = {
            'subject': 'Re: Escaped Reply Ticket',
            'body': '&lt;div dir="ltr"&gt;asdfgh&lt;/div&gt;&lt;br&gt;',
        }
        ticket.message_update(msg_dict)

        self.assertEqual(
            msg_dict['body'], '&lt;div dir="ltr"&gt;asdfgh&lt;/div&gt;&lt;br&gt;'
        )

    def test_07_reply_without_thread_headers_uses_ticket_number(self):
        """A reply with stripped mail headers still reaches its ticket chatter."""
        ticket = self.Ticket.create({
            'name': 'Subject-routed reply',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })

        routed_ticket = self.Ticket.message_new({
            'subject': '[Ticket #%s] Re: Subject-routed reply' % ticket.ticket,
            'body': '<p>Customer follow-up</p>',
            'from': self.partner.email,
        })

        self.assertEqual(routed_ticket, ticket)

    def test_08_ticket_cc_defaults_to_team_manager(self):
        """A new ticket copies the selected team's manager to CC."""
        manager = self.env['res.users'].create({
            'name': 'Support Manager',
            'login': 'support_manager_cc',
            'email': 'support.manager@example.com',
        })
        self.team.manager_id = manager

        ticket = self.Ticket.create({
            'name': 'Manager CC Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })

        self.assertEqual(ticket.email_cc_ids, manager.partner_id)

    def test_09_ticket_cc_keeps_selected_and_custom_recipients(self):
        """Explicit CC recipients are retained instead of the default."""
        manager = self.env['res.users'].create({
            'name': 'Support Manager Two',
            'login': 'support_manager_cc_two',
            'email': 'support.manager.two@example.com',
        })
        contact = self.Partner.create({
            'name': 'Customer Contact',
            'email': 'customer.contact@example.com',
        })
        custom_recipient = self.Partner.name_create('custom.recipient@example.com')
        self.team.manager_id = manager

        ticket = self.Ticket.create({
            'name': 'Explicit CC Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
            'email_cc_ids': [(6, 0, [contact.id, custom_recipient[0]])],
        })

        self.assertEqual(
            ticket.email_cc_ids,
            contact | self.Partner.browse(custom_recipient[0]),
        )
        self.assertNotIn(manager.partner_id, ticket.email_cc_ids)

    def test_10_ticket_email_templates_render_cc_recipients(self):
        """Every ticket notification template sends CC recipients as CC."""
        cc_one = self.Partner.create({
            'name': 'CC One',
            'email': 'cc.one@example.com',
        })
        cc_two = self.Partner.create({
            'name': 'CC Two',
            'email': 'cc.two@example.com',
        })
        ticket = self.Ticket.create({
            'name': 'Template CC Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
            'email_cc_ids': [(6, 0, [cc_one.id, cc_two.id])],
        })
        template_ids = (
            'cyllo_helpdesk.help_desk_mail_template',
            'cyllo_helpdesk.help_desk_in_progress_mail_template',
            'cyllo_helpdesk.help_desk_rating_template',
            'cyllo_helpdesk.help_desk_mail_template_auto_close_reminder',
        )

        for template_id in template_ids:
            rendered = self.env.ref(template_id)._generate_template(
                [ticket.id], ['email_cc'],
            )
            self.assertEqual(
                set(rendered[ticket.id]['email_cc'].split(',')),
                {'cc.one@example.com', 'cc.two@example.com'},
            )

    def test_11_ticket_email_keeps_cc_header(self):
        """Template delivery writes ticket CC recipients to mail.mail."""
        cc_recipient = self.Partner.create({
            'name': 'CC Header Recipient',
            'email': 'cc.header@example.com',
        })
        ticket = self.Ticket.create({
            'name': 'CC Header Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
            'email_cc_ids': [(6, 0, [cc_recipient.id])],
        })
        template = self.env.ref('cyllo_helpdesk.help_desk_mail_template')

        mail = self.env['mail.mail'].browse(
            template.send_mail(ticket.id, force_send=False)
        )

        self.assertEqual(mail.email_cc, 'cc.header@example.com')

    def test_12_ticket_email_templates_render_a_valid_reply_to(self):
        """Reply-To must be rendered, never a literal template statement."""
        ticket = self.Ticket.create({
            'name': 'Reply-To Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })
        template_ids = (
            'cyllo_helpdesk.help_desk_mail_template',
            'cyllo_helpdesk.help_desk_in_progress_mail_template',
            'cyllo_helpdesk.help_desk_rating_template',
            'cyllo_helpdesk.help_desk_mail_template_auto_close_reminder',
        )

        for template_id in template_ids:
            reply_to = self.env.ref(template_id)._render_field(
                'reply_to', [ticket.id],
            )[ticket.id] or ''
            self.assertNotIn('{%', reply_to)
            self.assertNotIn('%}', reply_to)

    def test_13_ticket_email_uses_threaded_team_reply_to(self):
        """Ticket emails use Cyllo's tracked reply route, not template text."""
        ticket = self.Ticket.create({
            'name': 'Reply-To Override Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })
        template = self.env.ref('cyllo_helpdesk.help_desk_mail_template')
        template.reply_to = '{% invalid template expression %}'

        mail = self.env['mail.mail'].browse(
            ticket._send_ticket_email(template, force_send=False)
        )

        self.assertNotIn('{%', mail.reply_to or '')
        self.assertEqual(
            mail.reply_to,
            ticket._notify_get_reply_to(default=mail.email_from)[ticket.id],
        )
        self.assertFalse(
            mail.recipient_ids,
            "The customer is already in email_to and must not receive a second mail.",
        )

    def test_14_ticket_email_templates_are_kept_in_chatter(self):
        """Sent ticket emails must not be deleted with their chatter entry."""
        for template_id in (
            'cyllo_helpdesk.help_desk_mail_template',
            'cyllo_helpdesk.help_desk_in_progress_mail_template',
            'cyllo_helpdesk.help_desk_rating_template',
            'cyllo_helpdesk.help_desk_mail_template_auto_close_reminder',
        ):
            self.assertFalse(self.env.ref(template_id).auto_delete)

    def test_15_automated_email_is_posted_on_ticket_chatter(self):
        """Replies to template emails must have a ticket message to thread on."""
        self.partner.email = 'customer@example.com'
        ticket = self.Ticket.create({
            'name': 'Chatter Threading Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })
        template = self.env.ref('cyllo_helpdesk.help_desk_mail_template')

        mail = self.env['mail.mail'].browse(
            ticket._send_ticket_email(template, force_send=False)
        )

        self.assertTrue(mail)
        self.assertEqual(mail.mail_message_id.model, 'helpdesk.ticket')
        self.assertEqual(mail.mail_message_id.res_id, ticket.id)
        self.assertEqual(mail.mail_message_id.message_type, 'comment')
        self.assertTrue(mail.mail_message_id.message_id)

    def test_16_in_progress_notification_is_different_from_new_ticket_email(self):
        """The In Progress transition must not resend the receipt email."""
        ticket = self.Ticket.create({
            'name': 'Status Notification Ticket',
            'team_id': self.team.id,
            'customer_id': self.partner.id,
        })
        received_template = self.env.ref(
            'cyllo_helpdesk.help_desk_mail_template',
        )
        in_progress_template = self.env.ref(
            'cyllo_helpdesk.help_desk_in_progress_mail_template',
        )

        received_subject = received_template._render_field(
            'subject', [ticket.id],
        )[ticket.id]
        in_progress_subject = in_progress_template._render_field(
            'subject', [ticket.id],
        )[ticket.id]

        self.assertIn('We received your ticket', received_subject)
        self.assertIn('We are working on your ticket', in_progress_subject)
        self.assertNotEqual(received_subject, in_progress_subject)
