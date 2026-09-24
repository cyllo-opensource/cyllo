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
import ast
import logging

from odoo import Command
from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)

class CommissionPlanController(Controller):
    """Users can choose preferred commission plan if they have multi plans"""

    @route('/thank-you', type='http', auth='user', website=True)
    def thank_you(self, **kw):
        """Render the thank you page after selecting a commission plan"""
        return request.render('cyllo_commission.thank_you_template')

    @route('/commissions', type='http', auth='user', website=True)
    def commission_plans(self, **kwargs):
        """Redirect to the page where users can choose the plan"""
        user = request.env.user
        current_company = request.env.company
        company_currency = current_company.currency_id
        type_ids = []
        single_type_id = request.params.get('type_id')
        if single_type_id and single_type_id.isdigit():
            type_ids.append(int(single_type_id))
        type_ids_param = request.params.get('type_ids')
        if type_ids_param:
            type_ids += [int(x) for x in type_ids_param.split(',') if
                         x.isdigit()]


        plans = request.env['commission.plan'].sudo().search([
            ('type_ids', 'in', type_ids), ('state', '=', 'approved'),
            ('sales_people_user_ids', 'in', user.id)
        ])
        active_plan = request.env['commission.plan'].sudo().search([
            ('type_ids', 'in', type_ids), ('state', '=', 'approved'),
            ('sales_people_user_ids', 'in', user.id),
            ('duplicate_user_ids', 'not in', user.id)
        ])
        return request.render(
            'cyllo_commission.commission_plan_template', {
                'user': user.id,
                'plans': plans,
                'active_plan': active_plan.id,
                'type_ids': type_ids,
                'currency_symbol': company_currency.symbol,
                'currency_position': company_currency.position
            })

    @route('/commission/submit', type='http', auth='user',
           methods=['POST'], csrf=True)
    def selected_commission_plan(self, **post):
        """Handle the submission of the selected commission plan"""
        new_active_plan = int(post.get('selected_plan'))
        plan_types_str = post.get('plan_types')
        type_ids = []
        if plan_types_str:
            try:
                type_ids = [int(x) for x in ast.literal_eval(plan_types_str)]
            except Exception as e:
                _logger.error("Invalid format for plan_types: %s",
                              plan_types_str)
        user = int(post.get('user'))
        active_plan = request.env['commission.plan'].sudo().search([
            ('type_ids', 'in', type_ids), ('state', '=', 'approved'),
            ('sales_people_user_ids', 'in', user),
            ('duplicate_user_ids', 'not in', user)
        ]).id
        if new_active_plan != active_plan:
            request.env['commission.plan'].sudo().browse(
                [new_active_plan]).write({
                'duplicate_user_ids': [Command.unlink(user)]
            })
            request.env['commission.plan'].sudo().browse(
                [active_plan]).write({
                'duplicate_user_ids': [Command.link(user)]
            })
        return request.redirect('/thank-you')
