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
from odoo import api, fields, models


class IrModule(models.Model):
    """Inherits ir.ui.menu to pass value to js and to add new fields."""
    _inherit = "ir.model"

    quick_create_show = fields.Boolean(string='Add to Quick Create',
                                       help="After enabling this can create a "
                                            "new form from navbar.")
    categories = fields.Selection(
        [('general', 'General'), ('sale', 'Sale'), ('purchase', 'Purchase'),
         ('accounting', 'Accounting')], string='Category', default='general',
        help="Select a category under which this form should be shown in the navbar.")
    fa_icon = fields.Selection(
        [('address-book', 'Address Book'), ('address-card', 'Address Card'),
         ('envelope-open', 'Envelope Open'), ('id-badge', 'Id Badge'),
         ('id-card', 'Id Card'),
         ('archive', 'Archive'), ('car', 'Car'), ('ban', 'Ban'),
         ('university', 'University'),
         ('battery-half', 'Battery Half'), ('battery-full', 'Battery Full'),
         ('bed', 'Bed'),
         ('bell', 'Bell'), ('bell-slash', 'Bell Slash'),
         ('bluetooth', 'Bluetooth'),
         ('bolt', 'Bolt'), ('bolt', 'Bomb'), ('book', 'Book'),
         ('bookmark', 'Bookmark'),
         ('briefcase', 'Briefcase'), ('bug', 'Bug'), ('bullhorn', 'Bullhorn'),
         ('bus', 'Bus'),
         ('taxi', 'Cab'), ('calendar', 'Calendar'), ('camera', 'Camera'),
         ('car', 'Car'),
         ('cart-plus', 'Cart'), ('cc', 'CC'), ('certificate', 'Certificate'),
         ('check', 'Check'),
         ('clone', 'Clone'), ('cloud', 'Cloud'), ('cog', 'Cog'),
         ('database', 'Database'),
         ('envelope', 'Envelope'), ('filter', 'Filter'), ('info', 'Info'),
         ('gavel', 'Legal'),
         ('location-arrow', 'Location Arrow'), ('lock', 'Lock'),
         ('money', 'Money'),
         ('music', 'Music'), ('paper-plane', 'Paper Plane'),
         ('pencil', 'Pencil'),
         ('percent', 'Percent'), ('phone', 'Phone'), ('plus', 'Plus'),
         ('print', 'Print'),
         ('puzzle-piece', 'Puzzle'), ('question', 'Question'),
         ('sitemap', 'Sitemap'),
         ('tachometer', 'Tachometer'), ('tasks', 'Tasks'), ('trash', 'Trash'),
         ('truck', 'Truck'), ('upload', 'Upload'), ('user', 'User'),
         ('video-camera', 'Video Camera'), ('volume-up', 'Volume'),
         ('exclamation-triangle', 'Warning'), ('exclamation-wrench', 'Wrench')],
        string='Item Icon',
        help="Select an icon to display the icon with the name of your "
             "model in the quick create section")

    @api.model
    def get_model(self):
        """When quick_create_show is True, models are searched using search_read()
        and the list is retrieved."""
        return self.sudo().search_read([('quick_create_show', '=', True)],
                                       ['categories', 'model', 'name',
                                        'fa_icon'])
