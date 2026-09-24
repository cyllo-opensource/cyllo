# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_cyllo_payroll_management = fields.Boolean(string="Install Payroll & Enable HR Dashboard")

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        menu = self.env.ref('cyllo_hr.menu_hr_dashboard_root', raise_if_not_found=False)
        if menu:
            menu.active = self.module_cyllo_payroll_management
