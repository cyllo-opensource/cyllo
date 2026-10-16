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
ANALYTICS_MODULE = 'cyllo_analytics'

APP_CATALOG = (
    (ANALYTICS_MODULE, 'Cyllo Analytics', 'analytics', 'charts and dashboards', ()),
    ('sale_management', 'Sales', 'sale_management', 'sales orders and quotations', ('sale.',)),
    ('purchase', 'Purchase', 'purchase', 'purchase orders and RFQs', ('purchase.',)),
    ('stock', 'Inventory', 'stock', 'stock, deliveries, receipts and warehouses', ('stock.',)),
    ('account', 'Invoicing', 'account', 'invoices, bills, payments and accounting', ('account.',)),
    ('mrp', 'Manufacturing', 'mrp', 'manufacturing orders and bills of materials', ('mrp.',)),
    ('crm', 'CRM', 'crm', 'leads and opportunities', ('crm.',)),
    ('project', 'Project', 'project', 'projects and tasks', ('project.',)),
    ('hr_timesheet', 'Timesheets', 'hr_timesheet', 'timesheets', ()),
    ('hr', 'Employees', 'hr', 'employees and departments', ('hr.employee', 'hr.department', 'hr.job')),
    ('hr_expense', 'Expenses', 'hr_expense', 'employee expenses', ('hr.expense',)),
    ('hr_holidays', 'Time Off', 'hr_holidays', 'leaves and time off', ('hr.leave',)),
    ('hr_attendance', 'Attendances', 'hr_attendance', 'attendances', ('hr.attendance',)),
    ('point_of_sale', 'Point of Sale', 'point_of_sale', 'POS orders and sessions', ('pos.',)),
    ('cyllo_helpdesk', 'Helpdesk', 'helpdesk', 'helpdesk tickets', ('helpdesk.',)),
    ('website', 'Website', 'website', 'the website, its pages and visitors', ('website',)),
    ('website_sale', 'eCommerce', 'website_sale', 'website / online shop orders and the web shop', ()),
    ('event', 'Events', 'event', 'events, registrations and attendees', ('event.',)),
    ('fleet', 'Fleet', 'fleet', 'vehicles, drivers and fleet costs', ('fleet.',)),
    ('hr_recruitment', 'Recruitment', 'hr_recruitment', 'job applicants and recruitment', ('hr.applicant', 'hr.recruitment')),
    ('cyllo_subscription', 'Subscriptions', 'cyllo_subscription', 'subscriptions and recurring orders', ('subscription.',)),
    ('survey', 'Surveys', 'survey', 'surveys and their answers', ('survey.',)),
    ('repair', 'Repairs', 'repair', 'repair orders', ('repair.',)),
    ('maintenance', 'Maintenance', 'maintenance', 'equipment maintenance requests', ('maintenance.',)),
)


DATA_HINTS = {
    'sale_management': "sale.order (lines: sale.order.line).",
    'website_sale': "there is NO website.order model: website orders are sale.order "
                    "records with [('website_id', '!=', False)]; normal sale orders "
                    "have [('website_id', '=', False)]. WHENEVER the user asks for a "
                    "sale order count or total, ALWAYS answer with three figures: "
                    "Sale orders (normal, no website), Website orders, and Total "
                    "(= normal + website). The count/aggregate tools return this split "
                    "as `website_split` — use it. Never add website orders on top of "
                    "an all-sale.order total.",
    'point_of_sale': "pos.order (lines: pos.order.line, sessions: pos.session); "
                     "completed states are paid, done (Posted) and invoiced.",
    'purchase': "purchase.order (lines: purchase.order.line).",
    'stock': "stock.picking (transfers), stock.move. On-hand stock = stock.quant "
             "quantity in internal locations, grouped by product_id (the tools add "
             "the internal-location filter automatically). Quants in virtual "
             "locations are negative mirrors — never report them as stock.",
    'account': "account.move (move_type out_invoice / in_invoice / out_refund / "
               "in_refund / entry), account.payment.",
    'crm': "crm.lead (type 'lead' or 'opportunity').",
    'project': "project.project, project.task.",
    'hr_timesheet': "account.analytic.line with project_id set.",
    'mrp': "mrp.production, mrp.bom.",
    'event': "event.event, event.registration.",
}


def install_marker(label, search):
    """The answer token the chat turns into an "Install" button opening Apps."""
    return f'[[install:{label}|{search}]]'


def _installed_names(env, names):
    rows = env['ir.module.module'].sudo().search_read(
        [('name', 'in', list(names)), ('state', '=', 'installed')], ['name'])
    return {r['name'] for r in rows}


def is_installed(env, module):
    """True when ``module`` is installed in this database."""
    return module in _installed_names(env, [module])


def app_statuses(env):
    """Every catalog entry as a dict, with its current ``installed`` flag."""
    installed = _installed_names(env, [a[0] for a in APP_CATALOG])
    return [
        {'module': m, 'label': l, 'search': s, 'covers': c, 'installed': m in installed}
        for m, l, s, c, _p in APP_CATALOG
    ]


def check_apps(env, names):
    """Look up apps by the user's words (technical name or title) across all
    modules, returning each match's install state and, if missing, its marker."""
    Module = env['ir.module.module'].sudo()
    results = []
    for name in names or []:
        term = (name or '').strip()
        if not term:
            continue
        mods = Module.search([('name', '=', term)], limit=1) or Module.search(
            ['|', ('shortdesc', 'ilike', term), ('name', 'ilike', term)],
            order='application desc, id', limit=1)
        if not mods:
            results.append({'app': term, 'status': 'not_found'})
            continue
        label = mods.shortdesc or mods.name
        entry = {'app': term, 'module': mods.name, 'label': label,
                 'status': 'installed' if mods.state == 'installed' else 'not_installed'}
        if entry['status'] == 'not_installed':
            entry['install_marker'] = install_marker(label, mods.name)
        results.append(entry)
    return results


def app_for_model(model):
    """The catalog entry providing ``model`` (by name prefix), or None."""
    for m, l, s, c, prefixes in APP_CATALOG:
        if any(model == p or model.startswith(p) for p in prefixes):
            return {'module': m, 'label': l, 'search': s, 'covers': c}
    return None


def not_installed_message(label, search, covers):
    """Tool/LLM message saying an app is missing, carrying the install marker."""
    return (f"The {label} app is not installed, so {covers} are not available. "
            f"Tell the user that the {label} app is not installed and that they "
            f"need to install it to get this. Put {install_marker(label, search)} "
            f"on its own line in your answer, copied literally (never as a Markdown "
            f"link) — it becomes an Install button. Do not query other models or "
            f"make up data for it.")
