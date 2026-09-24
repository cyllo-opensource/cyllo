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
from odoo import api, models


class Module(models.Model):
    """
    Customization of 'ir.module.module' model.
    """

    _inherit = 'ir.module.module'

    @api.model
    def app_install(self, app_ids):
        """
        Install selected applications.
        :param app_ids: List of application IDs to be installed.
        """
        apps = self.browse(app_ids)
        for app in apps:
            app.sudo().button_immediate_install()

    def get_child_app(self, module_ids, children_ids):
        """
        Recursively retrieve child applications.
        :param module_ids: List of module IDs.
        :param children_ids: List of child category IDs.
        :return: List of module IDs including child modules.
        """
        for categ in self.env['ir.module.category'].browse(
                children_ids).read(['id', 'child_ids', 'module_ids', 'name']):
            module_ids += categ.get('module_ids')
            if categ.get('child_ids'):
                self.get_child_app(module_ids, categ.get('child_ids'))
        return module_ids

    def custom_data(self):
        """
        Retrieve custom data related to installed and available applications.
        :return: Tuple of dictionaries with categories filtered by child applications.
        """
        installed_apps = self.env['ir.module.module'].search([]).filtered(
            lambda r: r.state == 'installed')
        categories_with_app = []
        categories_without_app = []
        categories = self.env['ir.module.category'].search_read(
            [('parent_id', '=', False)],
            ['id', 'child_ids', 'module_ids', 'name'])
        for categ in categories:
            module_ids = categ.get('module_ids', [])
            categ_ids = categ.get('child_ids')
            module_app_ids = self.get_child_app(module_ids, categ_ids)
            filtered_category_with_app = self.search(
                [('id', 'in', module_app_ids),
                 ('to_buy', '=', False)]).filtered(
                lambda
                    r: r.application and r not in installed_apps and r.state != 'uninstallable')
            filtered_category_without_app = self.browse(
                module_app_ids).filtered(
                lambda
                    r: r not in installed_apps and r.state != 'uninstallable')
            categories_with_app.append({
                'id': categ['id'],
                'name': categ['name'],
                'child_apps': filtered_category_with_app.read(
                    ['id', 'name', 'icon', 'shortdesc'])
            })
            categories_without_app.append({
                'id': categ['id'],
                'name': categ['name'],
                'child_apps': filtered_category_without_app.read(
                    ['id', 'name', 'icon', 'shortdesc'])
            })
        categories_with_app.sort(key=lambda x: len(x['child_apps']),
                                 reverse=True)
        categories_without_app.sort(key=lambda x: len(x['child_apps']),
                                    reverse=True)
        return categories_with_app, categories_without_app
