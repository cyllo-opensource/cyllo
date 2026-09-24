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
from odoo import models


class FieldServiceRequestReport(models.AbstractModel):
    """In this model we are defining the functions required for the class
        FieldServiceRequestReport:"""
    _name = "report.cyllo_field_service.report_field_service_request_xlsx"
    _description = 'Field service request report'

    def _get_report_values(self, docids, data=None):
        """
        Get the values for the field service request report.
        Returns:
            A dictionary containing the data needed for rendering the field service request report.
        """
        query_params = {}
        fs_request_report = self.env['field.service.report'].browse(
            data['context']['active_id'])
        query = """select field_service_request.name,res_partner.name as partner_name,field_service_skill_category.name 
        as category_name,field_service_request.priority,field_service_request.skill_category_id,
        field_service_request.company_id,field_service_request.create_date,date_deadline,sale_order.name as 
        sale_order_name, field_service_request.state from field_service_request inner join field_service_skill_category 
        on field_service_skill_category.id=field_service_request.skill_category_id inner join res_partner on 
        res_partner.id=field_service_request.partner_id left join sale_order on 
        sale_order.id=field_service_request.sale_order_id """
        query += f"""where field_service_request.company_id = '{self.env.company.id}' """
        request = self.env['field.service.request'].search([])
        if fs_request_report.filter == "customer_wise":
            if fs_request_report.partner_ids:
                query += " and res_partner.id IN %(partner_ids)s"
                query_params = {
                    'partner_ids': tuple(fs_request_report.partner_ids.ids)}
                request_domain = [
                    ('partner_id', 'in', fs_request_report.partner_ids.ids)]
                if fs_request_report.from_date:
                    request_domain.append(
                        ('create_date', '>=', fs_request_report.from_date))
                if fs_request_report.to_date:
                    request_domain.append(
                        ('create_date', '<=', fs_request_report.to_date))
                request = request.filtered_domain(request_domain)
        elif fs_request_report.filter == "sale_order_wise":
            if fs_request_report.sale_order_ids:
                query += " and sale_order.id IN %(sale_order_ids)s"
                query_params = {'sale_order_ids': tuple(
                    fs_request_report.sale_order_ids.ids)}
                request_domain = [('sale_order_id', 'in',
                                   fs_request_report.sale_order_ids.ids)]
                if fs_request_report.from_date:
                    request_domain.append(
                        ('create_date', '>=', fs_request_report.from_date))
                if fs_request_report.to_date:
                    request_domain.append(
                        ('create_date', '<=', fs_request_report.to_date))
                request = request.filtered_domain(request_domain)
        else:
            if fs_request_report.state:
                query += f"""and field_service_request.state = '{fs_request_report.state}' """
                request_domain = [('state', '=', fs_request_report.state)]
                if fs_request_report.from_date:
                    request_domain.append(
                        ('create_date', '>=', fs_request_report.from_date))
                if fs_request_report.to_date:
                    request_domain.append(
                        ('create_date', '<=', fs_request_report.to_date))
                request = request.filtered_domain(request_domain)
        if fs_request_report.from_date:
            query += f""" and field_service_request.create_date >= '{fs_request_report.from_date}' """
        if fs_request_report.to_date:
            query += f""" and field_service_request.create_date <= '{fs_request_report.to_date}' """
        self.env.cr.execute(query, query_params)
        datas = self.env.cr.dictfetchall()
        group_option = []
        if fs_request_report.group_by == 'priority':
            group_option = [['a', 'Low'], ['b', 'Medium'],
                            ['c', 'High'],
                            ['d', 'Very High']]
        if fs_request_report.group_by == 'state':
            group_option = [['draft', 'Draft'], ['submit', 'Submitted'],
                            ['assigned', 'Assigned'],
                            ['in_progress', 'In Progress'],
                            ['completed', 'Completed']]
        if fs_request_report.group_by == 'sale_order_id':
            sale_orders = request.mapped('sale_order_id').ids
            sale_details = self.env['sale.order'].browse(sale_orders)
            for sale in sale_details:
                group_option.append([sale.id, sale.name])
        if fs_request_report.group_by == 'skill_category_id':
            categories = request.mapped('skill_category_id').ids
            categories_details = self.env[
                'field.service.skill.category'].browse(categories)
            for category in categories_details:
                group_option.append([category.id, category.name])
        if fs_request_report.group_by == 'company_id':
            categories = request.mapped('company_id').ids
            categories_details = self.env['res.company'].browse(categories)
            for category in categories_details:
                group_option.append([category.id, category.name])
        if fs_request_report.group_by == 'none':
            group_option = []
        data['datas'] = datas
        data['group_option'] = group_option
        data['start_date'] = fs_request_report.from_date
        data['end_date'] = fs_request_report.to_date
        data['filter'] = fs_request_report.filter
        data['state'] = fs_request_report.state
        data['group_by'] = fs_request_report.group_by
        return data
