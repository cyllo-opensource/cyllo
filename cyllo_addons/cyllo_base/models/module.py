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
from textwrap import dedent

from odoo import api, models, modules
from odoo.addons.base.models.ir_module import assert_log_admin_access, Module
from odoo.http import request
from odoo.tools.misc import file_path
from odoo.tools.parse_version import parse_version

icons = {
    'Sales': '/cyllo_base/static/src/icons/sales.svg',
    'sale': '/cyllo_base/static/src/icons/sales.svg',
    'Restaurant': '/cyllo_base/static/src/icons/restaurant.svg',
    'pos_restaurant': '/cyllo_base/static/src/icons/restaurant.svg',
    'Invoicing': '/cyllo_base/static/src/icons/invoicing.svg',
    'Accounting': '/cyllo_base/static/src/icons/invoicing.svg',
    'account': '/cyllo_base/static/src/icons/invoicing.svg',
    'CRM': '/cyllo_base/static/src/icons/crm.svg',
    'crm': '/cyllo_base/static/src/icons/crm.svg',
    'Website': '/cyllo_base/static/src/icons/website.svg',
    'website': '/cyllo_base/static/src/icons/website.svg',
    'Inventory': '/cyllo_base/static/src/icons/inventory.svg',
    'stock': '/cyllo_base/static/src/icons/inventory.svg',
    'Purchase': '/cyllo_base/static/src/icons/purchase.svg',
    'purchase': '/cyllo_base/static/src/icons/purchase.svg',
    'Point of Sale': '/cyllo_base/static/src/icons/pos.svg',
    'point_of_sale': '/cyllo_base/static/src/icons/pos.svg',
    'Project': '/cyllo_base/static/src/icons/project.svg',
    'project': '/cyllo_base/static/src/icons/project.svg',
    'eCommerce': '/cyllo_base/static/src/icons/eCommerce.svg',
    'website_sale': '/cyllo_base/static/src/icons/eCommerce.svg',
    'Manufacturing': '/cyllo_base/static/src/icons/manufacturing.svg',
    'mrp': '/cyllo_base/static/src/icons/manufacturing.svg',
    'Email Marketing': '/cyllo_base/static/src/icons/email-marketing.svg',
    'mass_mailing': '/cyllo_base/static/src/icons/email-marketing.svg',
    'Expenses': '/cyllo_base/static/src/icons/expenses.svg',
    'hr_expense': '/cyllo_base/static/src/icons/expenses.svg',
    'Time Off': '/cyllo_base/static/src/icons/time-off.svg',
    'hr_holidays': '/cyllo_base/static/src/icons/time-off.svg',
    'Recruitment': '/cyllo_base/static/src/icons/recruitment.svg',
    'hr_recruitment': '/cyllo_base/static/src/icons/recruitment.svg',
    'Employees': '/cyllo_base/static/src/icons/employee.svg',
    'hr': '/cyllo_base/static/src/icons/employee.svg',
    'Data Recycle': '/cyllo_base/static/src/icons/data-recycling.svg',
    'data_recycle': '/cyllo_base/static/src/icons/data-recycling.svg',
    'Maintenance': '/cyllo_base/static/src/icons/maintenance.svg',
    'maintenance': '/cyllo_base/static/src/icons/maintenance.svg',
    'eLearning': '/cyllo_base/static/src/icons/eLearning.svg',
    'website_slides': '/cyllo_base/static/src/icons/eLearning.svg',
    'Events': '/cyllo_base/static/src/icons/events.svg',
    'website_event': '/cyllo_base/static/src/icons/events.svg',
    'Advanced Events': '/cyllo_base/static/src/icons/events.svg',
    'website_event_track': '/cyllo_base/static/src/icons/events.svg',
    'Events Organization': '/cyllo_base/static/src/icons/events.svg',
    'event': '/cyllo_base/static/src/icons/events.svg',
    'Online Event Ticketing': '/cyllo_base/static/src/icons/events.svg',
    'website_event_sale': '/cyllo_base/static/src/icons/events.svg',
    'Discuss': '/cyllo_base/static/src/icons/discuss.svg',
    'mail': '/cyllo_base/static/src/icons/discuss.svg',
    'Contacts': '/cyllo_base/static/src/icons/contact.svg',
    'contacts': '/cyllo_base/static/src/icons/contact.svg',
    'Calendar': '/cyllo_base/static/src/icons/calendar.svg',
    'calendar': '/cyllo_base/static/src/icons/calendar.svg',
    'Fleet': '/cyllo_base/static/src/icons/fleet.svg',
    'fleet': '/cyllo_base/static/src/icons/fleet.svg',
    'Live Chat': '/cyllo_base/static/src/icons/live-chat.svg',
    'im_livechat': '/cyllo_base/static/src/icons/live-chat.svg',
    'Surveys': '/cyllo_base/static/src/icons/survey.svg',
    'survey': '/cyllo_base/static/src/icons/survey.svg',
    'Task Logs': '/cyllo_base/static/src/icons/task-log.svg',
    'hr_timesheet': '/cyllo_base/static/src/icons/task-log.svg',
    'Repairs': '/cyllo_base/static/src/icons/repair.svg',
    'repair': '/cyllo_base/static/src/icons/repair.svg',
    'Attendances': '/cyllo_base/static/src/icons/attendance.svg',
    'hr_attendance': '/cyllo_base/static/src/icons/attendance.svg',
    'SMS Marketing': '/cyllo_base/static/src/icons/sms-marketing.svg',
    'mass_mailing_sms': '/cyllo_base/static/src/icons/sms-marketing.svg',
    'To-Do': '/cyllo_base/static/src/icons/todo.svg',
    'project_todo': '/cyllo_base/static/src/icons/todo.svg',
    'Skills Management': '/cyllo_base/static/src/icons/skill-management.svg',
    'hr_skills': '/cyllo_base/static/src/icons/skill-management.svg',
    'Lunch': '/cyllo_base/static/src/icons/lunch.svg',
    'lunch': '/cyllo_base/static/src/icons/lunch.svg',
    'Online Jobs': '/cyllo_base/static/src/icons/online-jobs.svg',
    'website_hr_recruitment': '/cyllo_base/static/src/icons/online-jobs.svg',
    'Employee Contracts': '/cyllo_base/static/src/icons/employee-contract.svg',
    'hr_contract': '/cyllo_base/static/src/icons/employee-contract.svg',
    'Blog': '/cyllo_base/static/src/icons/blog.svg',
    'website_blog': '/cyllo_base/static/src/icons/blog.svg',
    'Check Printing Base': '/cyllo_base/static/src/icons/check-printer-base.svg',
    'account_check_printing': '/cyllo_base/static/src/icons/check-printer-base.svg',
    'Contact Form': '/cyllo_base/static/src/icons/contact_form.svg',
    'website_crm': '/cyllo_base/static/src/icons/contact_form.svg',
    'Coupons, Promotions, Gift Card and Loyalty for eCommerce': '/cyllo_base/static/src/icons/Coupons-promotions.svg',
    'website_sale_loyalty': '/cyllo_base/static/src/icons/Coupons-promotions.svg',
    'Customer References': '/cyllo_base/static/src/icons/customer-reference.svg',
    'website_customer': '/cyllo_base/static/src/icons/customer-reference.svg',
    'Dashboards': '/cyllo_base/static/src/icons/dashboard.svg',
    'board': '/cyllo_base/static/src/icons/dashboard.svg',
    'Spreadsheet dashboard': '/cyllo_base/static/src/icons/dashboard.svg',
    'spreadsheet_dashboard': '/cyllo_base/static/src/icons/dashboard.svg',
    'Gamification': '/cyllo_base/static/src/icons/gamification.svg',
    'gamification': '/cyllo_base/static/src/icons/gamification.svg',
    'Google Calendar': '/cyllo_base/static/src/icons/google-calendar.svg',
    'google_calendar': '/cyllo_base/static/src/icons/google-calendar.svg',
    'Google Maps': '/cyllo_base/static/src/icons/google-maps.svg',
    'website_google_map': '/cyllo_base/static/src/icons/google-maps.svg',
    'In-App Purchases': '/cyllo_base/static/src/icons/in-app-purchases.svg',
    'iap': '/cyllo_base/static/src/icons/in-app-purchases.svg',
    'Link Tracker': '/cyllo_base/static/src/icons/link-tracker.svg',
    'link_tracker': '/cyllo_base/static/src/icons/link-tracker.svg',
    'Members': '/cyllo_base/static/src/icons/members.svg',
    'membership': '/cyllo_base/static/src/icons/members.svg',
    'Microsoft Outlook': '/cyllo_base/static/src/icons/microsoft-outlook.svg',
    'microsoft_outlook': '/cyllo_base/static/src/icons/microsoft-outlook.svg',
    'Newsletter Subscribe Button': '/cyllo_base/static/src/icons/newsletter-subscription.svg',
    'website_mass_mailing': '/cyllo_base/static/src/icons/newsletter-subscription.svg',
    'OdooBot': '/cyllo_base/static/src/icons/odoo-bots.svg',
    'mail_bot': '/cyllo_base/static/src/icons/odoo-bots.svg',
    'Online Members Directory': '/cyllo_base/static/src/icons/online-member-directory.svg',
    'website_membership': '/cyllo_base/static/src/icons/online-member-directory.svg',
    'Online Task Submission': '/cyllo_base/static/src/icons/online-task-submission.svg',
    'website_form_project': '/cyllo_base/static/src/icons/online-task-submission.svg',
    'On site Payment & Picking': '/cyllo_base/static/src/icons/Onsit-payment-picking.svg',
    'website_sale_picking': '/cyllo_base/static/src/icons/Onsit-payment-picking.svg',
    'Outlook Calendar': '/cyllo_base/static/src/icons/outlook-calendar.svg',
    'microsoft_calendar': '/cyllo_base/static/src/icons/outlook-calendar.svg',
    'Partner Autocomplete': '/cyllo_base/static/src/icons/partner-autocmplete.svg',
    'partner_autocomplete': '/cyllo_base/static/src/icons/partner-autocmplete.svg',
    'Payment Engine': '/cyllo_base/static/src/icons/payment-engine.svg',
    'payment': '/cyllo_base/static/src/icons/payment-engine.svg',
    'Products & Pricelists': '/cyllo_base/static/src/icons/pricelist.svg',
    'product': '/cyllo_base/static/src/icons/pricelist.svg',
    'Product Availability': '/cyllo_base/static/src/icons/product-availability.svg',
    'website_sale_stock': '/cyllo_base/static/src/icons/product-availability.svg',
    'Product Comparison': '/cyllo_base/static/src/icons/product-comparison.svg',
    'website_sale_comparison': '/cyllo_base/static/src/icons/product-comparison.svg',
    'Resellers': '/cyllo_base/static/src/icons/reseller.svg',
    'website_crm_partner_assign': '/cyllo_base/static/src/icons/reseller.svg',
    'Sales Timesheet': '/cyllo_base/static/src/icons/sales-timesheet.svg',
    'sale_timesheet': '/cyllo_base/static/src/icons/sales-timesheet.svg',
    "Shopper's Wishlist": '/cyllo_base/static/src/icons/shoppers-wishlist.svg',
    "website_sale_wishlist": '/cyllo_base/static/src/icons/shoppers-wishlist.svg',
    'SMS gateway': '/cyllo_base/static/src/icons/sms-gateway.svg',
    'sms': '/cyllo_base/static/src/icons/sms-gateway.svg',
    'Snail Mail': '/cyllo_base/static/src/icons/snailmail.svg',
    'snailmail': '/cyllo_base/static/src/icons/snailmail.svg',
    'Twitter Snippet': '/cyllo_base/static/src/icons/twitter-snippets.svg',
    'website_twitter': '/cyllo_base/static/src/icons/twitter-snippets.svg',
    'Work Entries - Contract': '/cyllo_base/static/src/icons/work-entries.svg',
    'hr_work_entry_contract': '/cyllo_base/static/src/icons/work-entries.svg',
}


class Module(models.Model):
    _inherit = 'ir.module.module'

    def next(self):
        res = super(Module, self).next()
        channel = "reset_menu"
        message = {"channel": channel}
        request.env["bus.bus"]._sendone(channel, "notification", message)
        return res

    @staticmethod
    def get_values_from_terp(terp):
        return {
            'description': dedent(terp.get('description', '')),
            'shortdesc': terp.get('name', ''),
            'author': terp.get('author', 'Unknown'),
            'maintainer': terp.get('maintainer', False),
            'contributors': ', '.join(terp.get('contributors', [])) or False,
            'website': terp.get('website', ''),
            'license': terp.get('license', 'LGPL-3'),
            'sequence': terp.get('sequence', 100),
            'application': terp.get('application', False),
            'auto_install': terp.get('auto_install', False) is not False,
            'icon': icons.get(terp.get('name')) or terp.get('icon', False),
            'summary': terp.get('summary', ''),
            'url': terp.get('url') or terp.get('live_test_url', ''),
            'to_buy': False
        }

    @assert_log_admin_access
    @api.model
    def update_list(self):
        res = [0, 0]  # [update, add]
        default_version = modules.adapt_version('1.0')
        known_mods = self.with_context(lang=None).search([])
        known_mods_names = {mod.name: mod for mod in known_mods}
        # iterate through detected modules and update/create them in db
        for mod_name in modules.get_modules():
            mod = known_mods_names.get(mod_name)
            terp = self.get_module_info(mod_name)
            values = self.get_values_from_terp(terp)
            if values['shortdesc'] in icons.keys():
                values['icon'] = icons[values['shortdesc']]
            if mod:
                updated_values = {}
                for key in values:
                    old = getattr(mod, key)
                    if (old or values[key]) and values[key] != old:
                        updated_values[key] = values[key]
                if terp.get('installable',
                            True) and mod.state == 'uninstallable':
                    updated_values['state'] = 'uninstalled'
                if parse_version(
                        terp.get('version', default_version)) > parse_version(
                        mod.latest_version or default_version):
                    res[0] += 1
                if mod.name == 'account':
                    # To Remove the Invoicing module from the app list
                    updated_values['to_buy'] = True
                if updated_values:
                    mod.write(updated_values)
            else:
                mod_path = modules.get_module_path(mod_name)
                if not mod_path or not terp:
                    continue
                state = "uninstalled" if terp.get('installable',
                                                  True) else "uninstallable"
                mod = self.create(dict(name=mod_name, state=state, **values))
                res[1] += 1
            mod._update_from_terp(terp)
        return res

    Module.update_list = update_list
    Module.get_values_from_terp = get_values_from_terp


def get_module_icon(module):
    fpath = f"{module}/static/description/icon.png"
    if module in icons.keys():
        path = icons[module]
        fpath = path[1:] if path.startswith('/') else path
    try:
        file_path(fpath)
        return "/" + fpath
    except FileNotFoundError:
        return "/cyllo_base/static/description/icon.svg"


def get_module_icon_path(module):
    try:
        return file_path(f"{module}/static/description/icon.png")
    except FileNotFoundError:
        return file_path("/cyllo_base/static/description/icon.svg")


modules.module.get_module_icon = get_module_icon
modules.module.get_module_icon_path = get_module_icon_path
