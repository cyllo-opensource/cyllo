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
##############################################################################
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval



class TestCrmSurveyBase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Lead = cls.env['crm.lead']
        cls.Survey = cls.env['survey.survey']
        cls.Question = cls.env['survey.question']
        cls.Input = cls.env['survey.user_input']
        cls.partner = cls.env['res.partner'].create({'name': 'Survey Partner'})

    def _field(self, name):
        return self.env['ir.model.fields']._get('crm.lead', name)

    def _survey(self, **vals):
        return self.Survey.create({
            'title': 'Flow Survey', 'create_lead': True, **vals})

    def _question(self, survey, question_type, field=None, **vals):
        return self.Question.create({
            'survey_id': survey.id,
            'title': 'Q %s' % (field or question_type),
            'question_type': question_type,
            'lead_field_id': self._field(field).id if field else False,
            **vals,
        })

    def _submit(self, survey, answers, partner=None, test_entry=False):
        """Create an answer sheet and mark it done; return the new lead."""
        user_input = self.Input.create({
            'survey_id': survey.id,
            'partner_id': partner.id if partner else False,
            'test_entry': test_entry,
        })
        for question, line_vals in answers:
            self.env['survey.user_input.line'].create({
                'user_input_id': user_input.id,
                'question_id': question.id,
                **line_vals,
            })
        before = self.Lead.search([])
        user_input._mark_done()
        self.user_input = user_input
        return self.Lead.search([]) - before

    @staticmethod
    def _char(value):
        return {'answer_type': 'char_box', 'value_char_box': value}


class TestLeadSurveyActions(TestCrmSurveyBase):

    def test_survey_count(self):
        lead = self.Lead.create({'name': 'L'})
        self.assertEqual(lead.survey_count, 0)
        self._survey(lead_id=lead.id)
        self._survey(lead_id=lead.id)
        self._survey()
        lead.invalidate_recordset()
        self.assertEqual(lead.survey_count, 2)

    def test_view_surveys_action_is_filtered_by_lead(self):
        lead = self.Lead.create({'name': 'L'})
        action = lead.action_view_surveys()
        self.assertEqual(action['domain'], [('lead_id', '=', lead.id)])
        self.assertEqual(action['context'], {'default_lead_id': lead.id})

    def test_create_survey_action_defaults(self):
        lead = self.Lead.create({'name': 'Big Deal'})
        action = lead.action_create_survey()
        self.assertEqual(action['res_model'], 'survey.survey')
        self.assertEqual(action['target'], 'current')
        self.assertEqual(action['context']['default_lead_id'], lead.id)
        self.assertEqual(action['context']['default_title'],
                         '%s Survey' % lead.display_name)

    def test_create_survey_action_enables_create_lead(self):
        lead = self.Lead.create({'name': 'Big Deal'})
        action = lead.action_create_survey()
        self.assertTrue(action['context']['default_create_lead'])
        survey = self.Survey.with_context(**action['context']).create(
            {'title': 'From lead'})
        self.assertTrue(survey.create_lead)
        self.assertEqual(survey.lead_id, lead)

    def test_survey_created_elsewhere_does_not_create_leads(self):
        self.assertFalse(self.Survey.create({'title': 'Plain'}).create_lead)

    def test_create_survey_action_without_lead(self):
        action = self.Lead.browse().action_create_survey()
        self.assertEqual(action['context']['default_title'], 'New Survey')
        self.assertFalse(action['context']['default_lead_id'])
        self.assertTrue(action['context']['default_create_lead'])

    def test_send_survey_prefills_lead_customer(self):
        lead = self.Lead.create({'name': 'L', 'partner_id': self.partner.id})
        survey = self._survey()
        self._question(survey, 'char_box')
        action = survey.with_context(
            default_lead_id=lead.id).action_send_survey()
        self.assertEqual(action['context']['default_partner_ids'],
                         [(6, 0, [self.partner.id])])

    def test_send_survey_without_customer_or_lead(self):
        survey = self._survey()
        self._question(survey, 'char_box')
        lead = self.Lead.create({'name': 'No customer'})
        for ctx in ({}, {'default_lead_id': lead.id}):
            action = survey.with_context(**ctx).action_send_survey()
            self.assertNotIn('default_partner_ids', action['context'])

    def test_menu_action_lists_only_lead_creating_surveys(self):
        action = self.env.ref('cyllo_crm_survey.action_survey_form_create_lead')
        domain = safe_eval(action.domain)
        mine = self._survey()
        other = self._survey(create_lead=False)
        surveys = self.Survey.search(domain)
        self.assertIn(mine, surveys)
        self.assertNotIn(other, surveys)


class TestQuestionFieldMapping(TestCrmSurveyBase):

    def _domain_types(self, question_type):
        question = self.Question.new({'question_type': question_type})
        domain = eval(question.lead_field_domain)
        self.assertEqual(domain[0], ('model', '=', 'crm.lead'))
        return domain[1]

    def test_domain_per_question_type(self):
        expected = {
            'char_box': {'char', 'many2one'},
            'text_box': {'char', 'text', 'many2one'},
            'numerical_box': {'integer', 'float', 'monetary'},
            'date': {'date'},
            'datetime': {'datetime'},
            'simple_choice': {'selection', 'many2one'},
            'multiple_choice': {'many2many', 'selection'},
        }
        for question_type, types in expected.items():
            clause = self._domain_types(question_type)
            self.assertEqual(clause[:2], ('ttype', 'in'), question_type)
            self.assertEqual(set(clause[2]), types, question_type)

    def test_matrix_questions_cannot_be_mapped(self):
        self.assertEqual(self._domain_types('matrix'), ('id', '=', False))

    def test_onchange_keeps_a_compatible_field(self):
        question = self._question(self._survey(), 'char_box', 'name')
        question.question_type = 'text_box'
        question._onchange_question_type()
        self.assertEqual(question.lead_field_id, self._field('name'))

    def test_onchange_clears_incompatible_field(self):
        for new_type in ('numerical_box', 'date', 'matrix'):
            question = self._question(self._survey(), 'char_box', 'name')
            question.question_type = new_type
            question._onchange_question_type()
            self.assertFalse(question.lead_field_id, new_type)

    def test_onchange_without_field_does_nothing(self):
        question = self._question(self._survey(), 'char_box')
        question.question_type = 'date'
        question._onchange_question_type()
        self.assertFalse(question.lead_field_id)


class TestLeadCreation(TestCrmSurveyBase):

    def test_no_lead_when_survey_does_not_create_leads(self):
        survey = self._survey(create_lead=False)
        question = self._question(survey, 'char_box', 'name')
        self.assertFalse(self._submit(survey, [(question, self._char('X'))]))

    def test_no_lead_for_test_entries(self):
        survey = self._survey()
        question = self._question(survey, 'char_box', 'name')
        self.assertFalse(self._submit(
            survey, [(question, self._char('X'))], test_entry=True))

    def test_lead_defaults(self):
        survey = self._survey()
        question = self._question(survey, 'char_box', 'name')
        lead = self._submit(survey, [(question, self._char('X'))])
        self.assertEqual(lead.type, 'opportunity')
        self.assertFalse(lead.user_id)

    def test_explicit_name_wins(self):
        survey = self._survey()
        name = self._question(survey, 'char_box', 'name')
        contact = self._question(survey, 'char_box', 'contact_name')
        lead = self._submit(survey, [
            (name, self._char('Deal A')), (contact, self._char('Ann'))])
        self.assertEqual(lead.name, 'Deal A')
        self.assertEqual(lead.contact_name, 'Ann')

    def test_name_from_contact(self):
        survey = self._survey()
        contact = self._question(survey, 'char_box', 'contact_name')
        lead = self._submit(survey, [(contact, self._char('Ann'))])
        self.assertEqual(lead.name, 'Ann - Opportunity')

    def test_name_from_company(self):
        survey = self._survey()
        company = self._question(survey, 'char_box', 'partner_name')
        lead = self._submit(survey, [(company, self._char('Acme'))])
        self.assertEqual(lead.name, 'Acme - Opportunity')

    def test_fallback_name_with_partner(self):
        survey = self._survey()
        question = self._question(survey, 'char_box', 'city')
        lead = self._submit(
            survey, [(question, self._char('Paris'))], partner=self.partner)
        self.assertEqual(lead.name, 'Flow Survey - Survey Partner')
        self.assertEqual(lead.partner_id, self.partner)
        self.assertEqual(lead.city, 'Paris')

    def test_fallback_name_anonymous(self):
        survey = self._survey()
        question = self._question(survey, 'char_box', 'city')
        lead = self._submit(survey, [(question, self._char('Paris'))])
        self.assertEqual(lead.name, 'Flow Survey - Anonymous')

    def test_text_answer(self):
        survey = self._survey()
        question = self._question(survey, 'text_box', 'description')
        lead = self._submit(survey, [(question, {
            'answer_type': 'text_box', 'value_text_box': 'Long text'})])
        self.assertIn('Long text', lead.description)

    def test_numeric_answers(self):
        survey = self._survey()
        revenue = self._question(survey, 'numerical_box', 'expected_revenue')
        color = self._question(survey, 'numerical_box', 'color')
        lead = self._submit(survey, [
            (revenue, {'answer_type': 'numerical_box',
                       'value_numerical_box': 1500.5}),
            (color, {'answer_type': 'numerical_box',
                     'value_numerical_box': 4.0})])
        self.assertEqual(lead.expected_revenue, 1500.5)
        self.assertEqual(lead.color, 4)

    def test_date_answer(self):
        survey = self._survey()
        question = self._question(survey, 'date', 'date_deadline')
        lead = self._submit(survey, [(question, {
            'answer_type': 'date', 'value_date': '2026-12-31'})])
        self.assertEqual(str(lead.date_deadline), '2026-12-31')

    def test_selection_answer_matches_label_case_insensitively(self):
        survey = self._survey()
        question = self._question(
            survey, 'simple_choice', 'priority',
            suggested_answer_ids=[(0, 0, {'value': 'VERY high'})])
        answer = question.suggested_answer_ids
        lead = self._submit(survey, [(question, {
            'answer_type': 'suggestion', 'suggested_answer_id': answer.id})])
        self.assertEqual(lead.priority, '3')

    def test_many2one_existing_record_is_reused(self):
        source = self.env['utm.source'].create({'name': 'Survey Source'})
        survey = self._survey()
        question = self._question(survey, 'char_box', 'source_id')
        lead = self._submit(survey, [(question, self._char('Survey Source'))])
        self.assertEqual(lead.source_id, source)

    def test_many2one_without_match_stays_empty(self):
        survey = self._survey()
        question = self._question(survey, 'char_box', 'source_id')
        lead = self._submit(survey, [(question, self._char('Nope Nope'))])
        self.assertFalse(lead.source_id)

    def test_customer_answer_reuses_exact_partner(self):
        survey = self._survey()
        question = self._question(survey, 'char_box', 'partner_id')
        lead = self._submit(survey, [(question, self._char('Survey Partner'))])
        self.assertEqual(lead.partner_id, self.partner)
        self.assertEqual(lead.name, 'Survey Partner - Opportunity')

    def test_customer_answer_creates_missing_partner(self):
        survey = self._survey()
        question = self._question(survey, 'char_box', 'partner_id')
        lead = self._submit(survey, [(question, self._char('Brand New Co'))])
        self.assertEqual(lead.partner_id.name, 'Brand New Co')

    def test_many2many_answer_links_existing_tag(self):
        tag = self.env['crm.tag'].create({'name': 'Survey Hot'})
        survey = self._survey()
        question = self._question(
            survey, 'multiple_choice', 'tag_ids',
            suggested_answer_ids=[(0, 0, {'value': 'Survey Hot'})])
        lead = self._submit(survey, [(question, {
            'answer_type': 'suggestion',
            'suggested_answer_id': question.suggested_answer_ids.id})])
        self.assertEqual(lead.tag_ids, tag)

    def test_unmapped_questions_are_ignored(self):
        survey = self._survey()
        mapped = self._question(survey, 'char_box', 'city')
        unmapped = self._question(survey, 'char_box')
        lead = self._submit(survey, [
            (mapped, self._char('Rome')), (unmapped, self._char('ignored'))])
        self.assertEqual(lead.city, 'Rome')
        self.assertNotIn('ignored', (lead.name or ''))

    def test_each_submission_creates_its_own_lead(self):
        survey = self._survey()
        question = self._question(survey, 'char_box', 'city')
        first = self._submit(survey, [(question, self._char('A'))])
        second = self._submit(survey, [(question, self._char('B'))])
        self.assertNotEqual(first, second)
        self.assertEqual((first.city, second.city), ('A', 'B'))

    def test_chatter_message_links_back_to_the_survey(self):
        survey = self._survey()
        question = self._question(survey, 'char_box', 'city')
        lead = self._submit(survey, [(question, self._char('Paris'))])
        body = str(lead.message_ids[:1].body)
        self.assertIn('Lead created from Survey:', body)
        self.assertIn('Flow Survey', body)
        self.assertIn('View User Input in Backend', body)
        self.assertIn('View Print Answers (Frontend)', body)
        self.assertIn(self.user_input.access_token, body)
        self.assertNotIn('%(', body)

    def test_chatter_message_is_rendered_html(self):
        survey = self._survey()
        question = self._question(survey, 'char_box', 'city')
        lead = self._submit(survey, [(question, self._char('Paris'))])
        body = str(lead.message_ids[:1].body)
        self.assertNotIn('&lt;', body)
        self.assertIn('<strong>Lead created from Survey:</strong>', body)
        self.assertEqual(body.count('<li>'), 2)
        self.assertIn(
            'href="/web#id=%s&amp;model=survey.survey&amp;view_type=form"'
            % survey.id, body)
        self.assertIn(
            'href="/web#id=%s&amp;model=survey.user_input&amp;view_type=form"'
            % self.user_input.id, body)
        self.assertIn(self.user_input.get_print_url().replace('&', '&amp;'),
                      body)

    def test_survey_title_is_escaped_in_chatter(self):
        survey = self._survey(title='<script>x</script>')
        question = self._question(survey, 'char_box', 'city')
        lead = self._submit(survey, [(question, self._char('Paris'))])
        self.assertNotIn('<script>', str(lead.message_ids[:1].body))


class TestLeadCreationEdgeCases(TestCrmSurveyBase):

    def _choice(self, question, answer):
        return (question, {'answer_type': 'suggestion',
                           'suggested_answer_id': answer.id})

    def test_survey_count_is_computed_per_lead(self):
        lead_a = self.Lead.create({'name': 'A'})
        lead_b = self.Lead.create({'name': 'B'})
        self._survey(lead_id=lead_a.id)
        self._survey(lead_id=lead_b.id)
        self._survey(lead_id=lead_b.id)
        leads = lead_a | lead_b
        leads.invalidate_recordset()
        self.assertEqual(lead_a.survey_count, 1)
        self.assertEqual(lead_b.survey_count, 2)

    def test_view_surveys_action_requires_a_single_lead(self):
        leads = self.Lead.create([{'name': 'A'}, {'name': 'B'}])
        with self.assertRaises(ValueError):
            leads.action_view_surveys()

    def test_submission_without_answers_still_creates_a_lead(self):
        survey = self._survey()
        self._question(survey, 'char_box', 'city')
        lead = self._submit(survey, [])
        self.assertEqual(lead.name, 'Flow Survey - Anonymous')
        self.assertEqual(lead.type, 'opportunity')

    def test_datetime_answer(self):
        survey = self._survey()
        question = self._question(survey, 'datetime', 'date_closed')
        lead = self._submit(survey, [(question, {
            'answer_type': 'datetime',
            'value_datetime': '2026-12-31 10:30:00'})])
        self.assertEqual(str(lead.date_closed), '2026-12-31 10:30:00')

    def test_float_answer(self):
        survey = self._survey()
        question = self._question(survey, 'numerical_box', 'probability')
        lead = self._submit(survey, [(question, {
            'answer_type': 'numerical_box', 'value_numerical_box': 33.5})])
        self.assertEqual(lead.probability, 33.5)

    def test_selection_answer_matches_the_technical_key(self):
        survey = self._survey()
        question = self._question(
            survey, 'simple_choice', 'priority',
            suggested_answer_ids=[(0, 0, {'value': '2'})])
        lead = self._submit(
            survey, [self._choice(question, question.suggested_answer_ids)])
        self.assertEqual(lead.priority, '2')

    def test_many2many_answer_falls_back_to_partial_match(self):
        tag = self.env['crm.tag'].create({'name': 'zzwarm lead'})
        survey = self._survey()
        question = self._question(
            survey, 'multiple_choice', 'tag_ids',
            suggested_answer_ids=[(0, 0, {'value': 'zzwarm'})])
        lead = self._submit(
            survey, [self._choice(question, question.suggested_answer_ids)])
        self.assertEqual(lead.tag_ids, tag)

    def test_many2many_answer_without_match_adds_no_tag(self):
        survey = self._survey()
        question = self._question(
            survey, 'multiple_choice', 'tag_ids',
            suggested_answer_ids=[(0, 0, {'value': 'zz-no-such-tag'})])
        lead = self._submit(
            survey, [self._choice(question, question.suggested_answer_ids)])
        self.assertFalse(lead.tag_ids)

    def test_many2many_answers_accumulate_tags(self):
        tags = self.env['crm.tag'].create([
            {'name': 'zzTagA'}, {'name': 'zzTagB'}])
        survey = self._survey()
        question = self._question(
            survey, 'multiple_choice', 'tag_ids',
            suggested_answer_ids=[
                (0, 0, {'value': 'zzTagA'}), (0, 0, {'value': 'zzTagB'})])
        lead = self._submit(survey, [
            self._choice(question, answer)
            for answer in question.suggested_answer_ids])
        self.assertEqual(lead.tag_ids, tags)

    def test_display_name_answer_is_used_as_the_lead_name(self):
        survey = self._survey()
        question = self._question(survey, 'char_box', 'display_name')
        lead = self._submit(survey, [(question, self._char('Named Deal'))])
        self.assertEqual(lead.name, 'Named Deal')

    def test_explicit_name_wins_over_customer_answer(self):
        survey = self._survey()
        name = self._question(survey, 'char_box', 'name')
        customer = self._question(survey, 'char_box', 'partner_id')
        lead = self._submit(survey, [
            (customer, self._char('Survey Partner')),
            (name, self._char('Chosen Name'))])
        self.assertEqual(lead.name, 'Chosen Name')
        self.assertEqual(lead.partner_id, self.partner)

    def test_customer_answer_overrides_respondent_partner(self):
        other = self.env['res.partner'].create({'name': 'Other Customer'})
        survey = self._survey()
        question = self._question(survey, 'char_box', 'partner_id')
        lead = self._submit(
            survey, [(question, self._char('Other Customer'))],
            partner=self.partner)
        self.assertEqual(lead.partner_id, other)

    def test_lead_is_created_for_every_answer_sheet_in_a_batch(self):
        survey = self._survey()
        question = self._question(survey, 'char_box', 'city')
        sheets = self.Input.create([
            {'survey_id': survey.id}, {'survey_id': survey.id}])
        for sheet, city in zip(sheets, ('Oslo', 'Rome')):
            self.env['survey.user_input.line'].create({
                'user_input_id': sheet.id, 'question_id': question.id,
                **self._char(city)})
        before = self.Lead.search([])
        sheets._mark_done()
        leads = self.Lead.search([]) - before
        self.assertEqual(set(leads.mapped('city')), {'Oslo', 'Rome'})
