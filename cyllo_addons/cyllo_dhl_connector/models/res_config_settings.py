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
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """
        This class inherits 'res.config.settings' model for using
        res config settings functionality
    """
    _inherit = "res.config.settings"

    dhl_express_connector = fields.Boolean(string="DHL Express",
                                           config_parameter="cyllo_dhl_connector.dhl_express_connector")

    def set_values(self):
        """
        Overrides the set_values method to create DHL data if the
        'DHL Express Connector' option is enabled. This method gets
        triggered when saving the configuration settings.
        """
        super(ResConfigSettings, self).set_values()
        dhl_carrier = self.env['delivery.carrier'].search([('delivery_type', '=', 'dhl')])
        if self.dhl_express_connector and not dhl_carrier:
            self.env['delivery.carrier'].create({
                'name': 'DHL Express',
                'delivery_type': 'dhl',
                'integration_level': 'rate_and_ship',
                'product_id': self.env.ref('cyllo_dhl_connector.product_product_dhl_shipping').id,
                'service_type': "1",
                'weight_uom': "KG",
                'dimension_unit': "CM",
                'region': "america",
                'label_template': "label",
                'label_format': 'PDF',
            })
        elif not self.dhl_express_connector and dhl_carrier:
            dhl_carrier.unlink()
