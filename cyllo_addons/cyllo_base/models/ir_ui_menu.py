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
import odoo
from odoo import api, fields, models
from odoo.tools.convert import nodeattr2bool, xml_import

ICONS = {
    "Discuss": "cyllo_base,static/src/icons/discuss.svg",
    "To-do": "cyllo_base,static/src/icons/todo.svg",
    "Sales": "cyllo_base,static/src/icons/sales.svg",
    "Dashboards": "cyllo_base,static/src/icons/dashboard.svg",
    "Invoicing": "cyllo_base,static/src/icons/invoicing.svg",
    "Accounting": "cyllo_base,static/src/icons/invoicing.svg",
    "Project": "cyllo_base,static/src/icons/project.svg",
    "Apps": "cyllo_base,static/src/icons/apps.svg",
    "Settings": "cyllo_base,static/src/icons/settings.svg",
    "Employees": "cyllo_base,static/src/icons/employee.svg",
    "CRM": "cyllo_base,static/src/icons/crm.svg",
    "Calendar": "cyllo_base,static/src/icons/calendar.svg",
    "Contacts": "cyllo_base,static/src/icons/contact.svg",
    "eLearning": "cyllo_base,static/src/icons/eLearning.svg",
    "Events": "cyllo_base,static/src/icons/events.svg",
    "Inventory": "cyllo_base,static/src/icons/inventory.svg",
    "Link Tracker": "cyllo_base,static/src/icons/link-tracker.svg",
    "Point of Sale": "cyllo_base,static/src/icons/pos.svg",
    "Purchase": "cyllo_base,static/src/icons/purchase.svg",
    "Manufacturing": "cyllo_base,static/src/icons/manufacturing.svg",
    "Website": "cyllo_base,static/src/icons/website.svg",
    "Email Marketing": "cyllo_base,static/src/icons/email-marketing.svg",
    "Expenses": "cyllo_base,static/src/icons/expenses.svg",
    "Time Off": "cyllo_base,static/src/icons/time-off.svg",
    "Timesheets": "cyllo_base,static/src/icons/task-log.svg",
    "Recruitment": "cyllo_base,static/src/icons/recruitment.svg",
    "Data Cleaning": "cyllo_base,static/src/icons/data-recycling.svg",
    "Maintenance": "cyllo_base,static/src/icons/maintenance.svg",
    "Fleet": "cyllo_base,static/src/icons/fleet.svg",
    "Live Chat": "cyllo_base,static/src/icons/live-chat.svg",
    "Surveys": "cyllo_base,static/src/icons/survey.svg",
    "Repairs": "cyllo_base,static/src/icons/repair.svg",
    "Attendances": "cyllo_base,static/src/icons/attendance.svg",
    "SMS Marketing": "cyllo_base,static/src/icons/sms-marketing.svg",
    "Members": "cyllo_base,static/src/icons/members.svg",
    "Lunch": "cyllo_base,static/src/icons/lunch.svg",
    "Demo": "cyllo_base,static/src/icons/demo_app-icon.svg",
}


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    add_to_shortcuts = fields.Boolean()
    is_studio = fields.Boolean(
        string="Studio Menu",
        default=False,
        help="Menu may customized or created through studio",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if "web_icon" in values:
                if values["name"] in ICONS.keys():
                    values["web_icon"] = ICONS[values["name"]]
            else:
                if not values.get("parent_id"):
                    values.update({"web_icon": ICONS["Demo"]})
        return super(IrUiMenu, self).create(vals_list)

    def write(self, vals):
        for record in self:
            if not record.is_studio and record.name in ICONS.keys():
                vals["web_icon"] = ICONS[record.name]
        res = super(IrUiMenu, self).write(vals)
        return res

    def _register_hook(self):
        super()._register_hook()
        from odoo.addons.cyllo_base.hooks import change_app_icons
        menus = self.env["ir.ui.menu"].search(
            [("parent_id", "=", False), ("name", "in", list(ICONS.keys()))]
        )
        for menu in menus:
            icon = ICONS[menu.name]
            if menu.web_icon != icon:
                menu.web_icon = icon
        change_app_icons(self.env)

    @api.model
    def get_action_home_id(self):
        root = self.env.ref(
            "cyllo_dashboard.menu_cyllo_dashboard_root", raise_if_not_found=False
        )
        if not root:
            return False
        return {"id": root.id, "active": root.active}

    def _tag_menuitem(self, rec, parent=None):
        rec_id = rec.attrib["id"]
        self._test_xml_id(rec_id)
        # The parent attribute was specified, if non-empty determine its ID,
        # otherwise explicitly make a top-level menu
        values = {
            "parent_id": False,
            "active": nodeattr2bool(rec, "active", default=True),
        }
        if rec.get("sequence"):
            values["sequence"] = int(rec.get("sequence"))
        if parent is not None:
            values["parent_id"] = parent
        elif rec.get("parent"):
            values["parent_id"] = self.id_get(rec.attrib["parent"])
        if rec.get("web_icon"):
            values["web_icon"] = (
                ICONS.get(rec.attrib["name"])
                if rec.attrib["name"] in ICONS.keys()
                else rec.attrib["web_icon"]
            )
        if rec.get("name"):
            values["name"] = rec.attrib["name"]
        if rec.get("action"):
            a_action = rec.attrib["action"]
            if "." not in a_action:
                a_action = "%s.%s" % (self.module, a_action)
            act = self.env.ref(a_action).sudo()
            values["action"] = "%s,%d" % (act.type, act.id)
            if (
                not values.get("name")
                and act.type.endswith(
                    ("act_window", "wizard", "url", "client", "server")
                )
                and act.name
            ):
                values["name"] = act.name
        if not values.get("name"):
            values["name"] = rec_id or "?"
        groups = []
        for group in rec.get("groups", "").split(","):
            if group.startswith("-"):
                group_id = self.id_get(group[1:])
                groups.append(odoo.Command.unlink(group_id))
            elif group:
                group_id = self.id_get(group)
                groups.append(odoo.Command.link(group_id))
        if groups:
            values["groups_id"] = groups
        data = {
            "xml_id": self.make_xml_id(rec_id),
            "values": values,
            "noupdate": self.noupdate,
        }
        menu = self.env["ir.ui.menu"]._load_records([data], self.mode == "update")
        for child in rec.iterchildren("menuitem"):
            self._tag_menuitem(child, parent=menu.id)

    xml_import._tag_menuitem = _tag_menuitem
